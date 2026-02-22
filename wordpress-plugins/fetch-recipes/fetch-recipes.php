<?php
/**
 * Plugin Name: Fetch Recipes from API (WP Delicious Integration)
 * Description: Fetches recipes from Django API and maps them to WP Delicious plugin format.
 * Version: 2.2
 * Author: Łukasz Segin
 */

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly.
}

require_once plugin_dir_path(__FILE__) . 'fetch_recipes_admin.php';

function fr_activate_plugin() {
    if (!wp_next_scheduled('fr_fetch_recipes_event')) {
        wp_schedule_event(time(), 'hourly', 'fr_fetch_recipes_event');
    }
    fr_fetch_and_create_recipes();
}
register_activation_hook(__FILE__, 'fr_activate_plugin');

function fr_deactivate_plugin() {
    wp_clear_scheduled_hook( 'fr_fetch_recipes_event' );
}
register_deactivation_hook( __FILE__, 'fr_deactivate_plugin' );

add_action( 'fr_fetch_recipes_event', 'fr_fetch_and_create_recipes' );

/**
 * Main Logic
 */
function fr_fetch_and_create_recipes() {
    $results = array('created' => 0, 'updated' => 0, 'errors' => 0);

    error_log('[FR] === STARTING RECIPE FETCH PROCESS ===');

    // Endpoint API
    $api_url = 'http://localhost:8000/api/recipes/';

    error_log('[FR] Fetching from: ' . $api_url);

    $response = wp_remote_get($api_url, array('timeout' => 30, 'sslverify' => false));

    if (is_wp_error($response)) {
        error_log('[FR] Fetch Recipes ERROR: ' . $response->get_error_message());
        return false;
    }

    $recipes = json_decode(wp_remote_retrieve_body($response), true);

    if (empty($recipes) || !is_array($recipes)) {
        error_log('[FR] Fetch Recipes ERROR: Invalid JSON response or empty array.');
        return false;
    }

    error_log('[FR] Successfully parsed JSON. Found ' . count($recipes) . ' recipes.');

    foreach ($recipes as $recipe) {
        $recipe_id = isset($recipe['id']) ? $recipe['id'] : null;
        if (!$recipe_id) {
            error_log('[FR] Skipping recipe without ID.');
            continue;
        }

        error_log("[FR] Processing API Recipe ID: {$recipe_id}, Title: " . (isset($recipe['title']) ? $recipe['title'] : 'Unknown'));

        $existing_posts = new WP_Query(array(
            'post_type'  => 'recipe',
            'post_status' => array('publish', 'draft', 'pending', 'private'),
            'meta_key'   => 'fr_recipe_id',
            'meta_value' => $recipe_id,
            'fields'     => 'ids'
        ));

        // Mapowanie danych do struktury wtyczki
        $delicious_meta = fr_map_recipe_to_delicious_meta($recipe);
        $post_title = isset($recipe['title']) ? $recipe['title'] : 'Untitled Recipe';

        // Wypełnianie treści posta (Priorytet dla blog_content z HTML)
        if (!empty($recipe['blog_content'])) {
            $post_content = $recipe['blog_content'];
        } else {
            // Fallback dla starszych przepisów bez blog_content
            $post_content = isset($recipe['description']) ? $recipe['description'] : 'Przepis wygenerowany automatycznie.';
            $post_content = '<p>' . nl2br($post_content) . '</p>';
        }

        $post_data = array(
            'post_title'   => wp_strip_all_tags($post_title),
            'post_content' => $post_content,
            'post_status'  => 'draft',
            'post_author'  => 1,
            'post_type'    => 'recipe',
            'post_date'    => current_time('mysql')
        );

        if ($existing_posts->have_posts()) {
            // UPDATE
            $post_id = $existing_posts->posts[0];
            error_log("[FR] Found existing Post ID: {$post_id}. Checking timestamps...");

            $last_updated = get_post_meta($post_id, 'fr_recipe_updated_at', true);
            $recipe_updated = isset($recipe['updated_at']) ? $recipe['updated_at'] : '';

            if (empty($last_updated) || empty($recipe_updated) || $recipe_updated > $last_updated) {
                error_log("[FR] Updating Post ID: {$post_id}");
                $post_data['ID'] = $post_id;
                wp_update_post($post_data, true);

                fr_update_recipe_meta($post_id, $delicious_meta, $recipe_id, $recipe_updated);

                // Obsługa obrazka
                if (isset($recipe['image_url']) && !empty($recipe['image_url'])) {
                    error_log("[FR] Image URL found for update: " . $recipe['image_url']);
                    fr_set_featured_image($post_id, $recipe['image_url']);
                } else {
                    error_log("[FR] No image_url provided for API Recipe ID: {$recipe_id}");
                }

                $results['updated']++;
            } else {
                error_log("[FR] Recipe ID {$recipe_id} is up to date.");
            }
        } else {
            // INSERT
            error_log("[FR] Creating NEW post for API Recipe ID: {$recipe_id}");
            $post_id = wp_insert_post($post_data, true);

            if (!is_wp_error($post_id)) {
                error_log("[FR] New post created successfully. WP Post ID: {$post_id}");
                fr_update_recipe_meta($post_id, $delicious_meta, $recipe_id, isset($recipe['updated_at']) ? $recipe['updated_at'] : '');

                // Obsługa obrazka
                if (isset($recipe['image_url']) && !empty($recipe['image_url'])) {
                    error_log("[FR] Image URL found for new post: " . $recipe['image_url']);
                    fr_set_featured_image($post_id, $recipe['image_url']);
                } else {
                    error_log("[FR] No image_url provided for new post API Recipe ID: {$recipe_id}");
                }

                $results['created']++;
            } else {
                error_log("[FR] Error creating post: " . $post_id->get_error_message());
                $results['errors']++;
            }
        }
    }
    update_option('fr_last_fetch_time', time());
    error_log("[FR] === PROCESS COMPLETE. Created: {$results['created']}, Updated: {$results['updated']}, Errors: {$results['errors']} ===");
    return $results;
}

/**
 * Funkcja aktualizująca metadane (POPRAWIONA o brakujące flagi graficzne)
 */
function fr_update_recipe_meta($post_id, $delicious_meta, $api_id, $api_updated_at) {
    error_log("[FR] Updating META for Post ID: {$post_id}");

    // 1. Główne dane przepisu
    update_post_meta($post_id, 'delicious_recipes_metadata', $delicious_meta);

    // 2. Pola pomocnicze i flagi widoczności
    $difficulty = isset($delicious_meta['difficultyLevel']) ? $delicious_meta['difficultyLevel'] : 'beginner';
    $season = isset($delicious_meta['bestSeason']) ? $delicious_meta['bestSeason'] : 'summer';

    update_post_meta($post_id, '_dr_difficulty_level', $difficulty);
    update_post_meta($post_id, '_dr_best_season', $season);

    // !!! WAŻNE: To pole aktywuje wyświetlanie karty przepisu (grafiki) na stronie !!!
    $widget_active = update_post_meta($post_id, '_drwidgetsblocks_active', 'yes');
    if ($widget_active) {
        error_log("[FR] Set _drwidgetsblocks_active to 'yes' for Post ID: {$post_id}");
    }

    // 3. Generowanie prostej listy składników (wymagane przez wtyczkę)
    $simple_ingredients = array();
    $ing_count = 0;

    if (!empty($delicious_meta['recipeIngredients'][0]['ingredients'])) {
        $ingredients_raw = $delicious_meta['recipeIngredients'][0]['ingredients'];
        $ing_count = count($ingredients_raw);

        foreach ($ingredients_raw as $ing_item) {
            if (!empty($ing_item['ingredient'])) {
                $simple_ingredients[] = $ing_item['ingredient'];
            }
        }
    }

    error_log("[FR] Ingredients count for Post ID {$post_id}: {$ing_count}");
    update_post_meta($post_id, '_dr_ingredient_count', $ing_count);
    update_post_meta($post_id, '_dr_recipe_ingredients', $simple_ingredients);

    // 4. Synchronizacja
    update_post_meta($post_id, 'fr_recipe_id', $api_id);
    if (!empty($api_updated_at)) {
        update_post_meta($post_id, 'fr_recipe_updated_at', $api_updated_at);
    }
}

/**
 * Mapper Function: Converts Django API text to WP Delicious array structure
 */
function fr_map_recipe_to_delicious_meta($recipe) {
    $raw_instructions = isset($recipe['instructions']) ? $recipe['instructions'] : '';
    $ingredients_list = [];
    $instructions_list = [];

    // Składniki
    if (preg_match('/#\s*Ingredients(.*?)(?=#|$)/s', $raw_instructions, $m)) {
        $lines = preg_split('/^\s*-\s*/m', trim($m[1]), -1, PREG_SPLIT_NO_EMPTY);
        foreach ($lines as $line) {
            $ingredients_list[] = [
                'quantity' => '',
                'unit' => '',
                'ingredient' => trim($line),
                'notes' => ''
            ];
        }
    }

    // Instrukcje
    if (preg_match('/#\s*Instructions(.*?)(?=#|$)/s', $raw_instructions, $m)) {
        $lines = preg_split('/^\s*\d+\.\s*/m', trim($m[1]), -1, PREG_SPLIT_NO_EMPTY);
        foreach ($lines as $line) {
            $instructions_list[] = [
                'instructionTitle' => '',
                'instruction' => trim($line),
                'image' => '',
                'videoURL' => '',
                'instructionNotes' => ''
            ];
        }
    }

    // Czasy
    $prep_time = '15'; $cook_time = '15';
    if (preg_match('/Prep Time:\s*(\d+)/', $raw_instructions, $m)) $prep_time = $m[1];
    if (preg_match('/Cook Time:\s*(\d+)/', $raw_instructions, $m)) $cook_time = $m[1];

    // Wyciąganie Kalorii z surowych instrukcji
    $calories = '';
    if (preg_match('/Calories:\s*([^\n]+)/', $raw_instructions, $m)) {
        if (trim($m[1]) !== 'Brak danych') {
            $calories = trim($m[1]) . ' kcal';
        }
    }

    // Wyciąganie słów kluczowych (jeśli LLM je zwrócił w description lub instrukcjach)
    $keywords = !empty($recipe['keywords']) ? $recipe['keywords'] : 'domowe, obiad';

    // 1. Pobranie surowych danych z API
    $raw_difficulty = !empty($recipe['difficulty']) ? strtolower(trim($recipe['difficulty'])) : 'beginner';
    $raw_season = !empty($recipe['season']) ? strtolower(trim($recipe['season'])) : 'all_year';

    // 2. Słowniki tłumaczeń na język polski
    $difficulty_translations = [
        'beginner'     => 'Łatwy',
        'intermediate' => 'Średni',
        'advanced'     => 'Trudny'
    ];

    $season_translations = [
        'spring'   => 'Wiosna',
        'summer'   => 'Lato',
        'autumn'   => 'Jesień',
        'winter'   => 'Zima',
        'all_year' => 'Cały rok'
    ];

    // 3. Mapowanie na polskie nazwy (jeśli API zwróci coś dziwnego, użyjemy domyślnych)
    $difficulty = isset($difficulty_translations[$raw_difficulty]) ? $difficulty_translations[$raw_difficulty] : 'Łatwy';
    $season = isset($season_translations[$raw_season]) ? $season_translations[$raw_season] : 'Cały rok';

    return [
        'recipeSubtitle'    => '',
        'recipeDescription' => isset($recipe['description']) ? $recipe['description'] : '',
        'recipeKeywords'    => $keywords,
        'difficultyLevel'   => $difficulty,
        'prepTime'          => $prep_time,
        'prepTimeUnit'      => 'min',
        'cookTime'          => $cook_time,
        'cookTimeUnit'      => 'min',
        'restTime'          => '0',
        'restTimeUnit'      => 'min',
        'totalDuration'     => (int)$prep_time + (int)$cook_time,
        'totalDurationUnit' => 'min',
        'bestSeason'        => $season,
        'recipeCalories'    => $calories,
        'noOfServings'      => '4',
        'ingredientTitle'   => 'Składniki',
        'recipeIngredients' => [[
            'sectionTitle' => '',
            'ingredients'  => $ingredients_list
        ]],
        'instructionsTitle' => 'Sposób przygotowania',
        'recipeInstructions'=> [[
            'sectionTitle' => '',
            'instruction'  => $instructions_list
        ]],
        'recipeNotes'       => 'Wygenerowano automatycznie przez AI Cooking App.',
        'imageGalleryImages'=> [],
        'videoGalleryVids'  => []
    ];
}


/**
 * Featured Image - Funkcja pobierająca i ustawiająca obrazek
 */
function fr_set_featured_image($post_id, $image_url) {
    if (has_post_thumbnail($post_id)) {
        error_log("[FR] Post ID {$post_id} already has a featured image. Skipping.");
        return true;
    }

    $clean_url = trim($image_url);
    $clean_url = esc_url_raw($clean_url);

    error_log("[FR] Attempting to set Featured Image for Post ID {$post_id}. URL: {$clean_url}");

    if (empty($clean_url) || !filter_var($clean_url, FILTER_VALIDATE_URL)) {
        error_log("[FR] Invalid URL format for image: {$clean_url}");
        return false;
    }

    require_once(ABSPATH . 'wp-admin/includes/media.php');
    require_once(ABSPATH . 'wp-admin/includes/file.php');
    require_once(ABSPATH . 'wp-admin/includes/image.php');

    // Używamy wp_remote_get(), które nie blokuje portu 8000 ani localhosta
    $response = wp_remote_get($clean_url, array(
        'timeout'   => 30,
        'sslverify' => false
    ));

    if (is_wp_error($response)) {
        error_log('[FR] Error downloading image (wp_remote_get): ' . $response->get_error_message());
        return false;
    }

    $response_code = wp_remote_retrieve_response_code($response);
    if ($response_code !== 200) {
        error_log("[FR] Failed to download image. HTTP Status: {$response_code}");
        return false;
    }

    $image_data = wp_remote_retrieve_body($response);
    if (empty($image_data)) {
        error_log('[FR] Downloaded image body is empty.');
        return false;
    }

    // Wyciągamy oryginalną nazwę pliku
    $filename = basename(parse_url($clean_url, PHP_URL_PATH));
    if (empty($filename)) {
        $filename = 'recipe_image_' . $post_id . '.png';
    }

    // Tworzymy plik tymczasowy w WordPress
    $tmp = wp_tempnam($filename);
    if (!$tmp) {
        error_log('[FR] Could not create temp file for image.');
        return false;
    }

    // Zapisujemy pobrane dane obrazka do pliku tymczasowego
    file_put_contents($tmp, $image_data);

    error_log("[FR] Image manually downloaded and saved to temp: {$tmp}");

    $file_array = array(
        'name'     => $filename,
        'tmp_name' => $tmp
    );

    // Import do biblioteki mediów
    $attachment_id = media_handle_sideload($file_array, $post_id);

    if (is_wp_error($attachment_id)) {
        @unlink($tmp);
        error_log('[FR] Error saving image/sideloading: ' . $attachment_id->get_error_message());
        return false;
    }

    error_log("[FR] Created Attachment ID: {$attachment_id}. Setting as featured image...");

    // Ustawienie jako Featured Image
    set_post_thumbnail($post_id, $attachment_id);
    return true;
}