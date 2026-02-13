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

    // Endpoint API
    // Upewnij się, że adres jest poprawny dla Twojej konfiguracji (localhost lub nazwa serwisu docker)
    $api_url = 'http://localhost:8000/api/recipes/';

    $response = wp_remote_get($api_url, array('timeout' => 30, 'sslverify' => false));

    if (is_wp_error($response)) {
        error_log('Fetch Recipes ERROR: ' . $response->get_error_message());
        return false;
    }

    $recipes = json_decode(wp_remote_retrieve_body($response), true);

    if (empty($recipes) || !is_array($recipes)) {
        error_log('Fetch Recipes ERROR: Invalid JSON response.');
        return false;
    }

    foreach ($recipes as $recipe) {
        $recipe_id = isset($recipe['id']) ? $recipe['id'] : null;
        if (!$recipe_id) continue;

        $existing_posts = new WP_Query(array(
            'post_type'  => 'recipe',
            'meta_key'   => 'fr_recipe_id',
            'meta_value' => $recipe_id,
            'fields'     => 'ids'
        ));

        // Mapowanie danych do struktury wtyczki
        $delicious_meta = fr_map_recipe_to_delicious_meta($recipe);
        $post_title = isset($recipe['title']) ? $recipe['title'] : 'Untitled Recipe';

        // Wypełnianie treści posta (dla SEO i wyglądu)
        $post_content = isset($recipe['description']) ? $recipe['description'] : '';
        if (empty($post_content)) {
            $post_content = 'Przepis wygenerowany automatycznie.';
        }
        $post_content = '<p>' . nl2br($post_content) . '</p>';

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
            $last_updated = get_post_meta($post_id, 'fr_recipe_updated_at', true);
            $recipe_updated = isset($recipe['updated_at']) ? $recipe['updated_at'] : '';

            if (empty($last_updated) || empty($recipe_updated) || $recipe_updated > $last_updated) {
                $post_data['ID'] = $post_id;
                wp_update_post($post_data, true);

                fr_update_recipe_meta($post_id, $delicious_meta, $recipe_id, $recipe_updated);

                // Obsługa obrazka
                if (isset($recipe['image_url']) && !empty($recipe['image_url'])) {
                    fr_set_featured_image($post_id, $recipe['image_url']);
                }

                $results['updated']++;
            }
        } else {
            // INSERT
            $post_id = wp_insert_post($post_data, true);
            if (!is_wp_error($post_id)) {
                fr_update_recipe_meta($post_id, $delicious_meta, $recipe_id, isset($recipe['updated_at']) ? $recipe['updated_at'] : '');

                // Obsługa obrazka
                if (isset($recipe['image_url']) && !empty($recipe['image_url'])) {
                    fr_set_featured_image($post_id, $recipe['image_url']);
                }

                $results['created']++;
            }
        }
    }
    update_option('fr_last_fetch_time', time());
    return $results;
}

/**
 * Funkcja aktualizująca metadane (POPRAWIONA o brakujące flagi graficzne)
 */
function fr_update_recipe_meta($post_id, $delicious_meta, $api_id, $api_updated_at) {
    // 1. Główne dane przepisu
    update_post_meta($post_id, 'delicious_recipes_metadata', $delicious_meta);

    // 2. Pola pomocnicze i flagi widoczności (KLUCZOWE POPRAWKI)
    update_post_meta($post_id, '_dr_difficulty_level', 'beginner');
    update_post_meta($post_id, '_dr_best_season', 'summer');

    // !!! WAŻNE: To pole aktywuje wyświetlanie karty przepisu (grafiki) na stronie !!!
    update_post_meta($post_id, '_drwidgetsblocks_active', 'yes');

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

    return [
        'recipeSubtitle'    => '',
        'recipeDescription' => isset($recipe['description']) ? $recipe['description'] : '',
        'recipeKeywords'    => '',
        'difficultyLevel'   => 'beginner',
        'prepTime'          => $prep_time,
        'prepTimeUnit'      => 'min',
        'cookTime'          => $cook_time,
        'cookTimeUnit'      => 'min',
        'restTime'          => '0',
        'restTimeUnit'      => 'min',
        'totalDuration'     => (int)$prep_time + (int)$cook_time,
        'totalDurationUnit' => 'min',
        'bestSeason'        => 'summer',
        'recipeCalories'    => '',
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
    if (has_post_thumbnail($post_id)) return true; // Już ma obrazek

    require_once(ABSPATH . 'wp-admin/includes/media.php');
    require_once(ABSPATH . 'wp-admin/includes/file.php');
    require_once(ABSPATH . 'wp-admin/includes/image.php');

    // Pobranie pliku do temp
    $tmp = download_url($image_url);
    if (is_wp_error($tmp)) {
        error_log('Error downloading image: ' . $tmp->get_error_message());
        return false;
    }

    $file_array = array(
        'name' => basename($image_url),
        'tmp_name' => $tmp
    );

    // Import do biblioteki mediów
    $attachment_id = media_handle_sideload($file_array, $post_id);

    if (is_wp_error($attachment_id)) {
        @unlink($tmp);
        error_log('Error saving image: ' . $attachment_id->get_error_message());
        return false;
    }

    // Ustawienie jako Featured Image
    set_post_thumbnail($post_id, $attachment_id);
    return true;
}