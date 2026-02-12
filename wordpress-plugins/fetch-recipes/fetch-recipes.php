<?php
/**
 * Plugin Name: Fetch Recipes from API (WP Delicious Integration)
 * Description: Fetches recipes from Django API and maps them to WP Delicious plugin format.
 * Version: 2.1
 * Author: Łukasz Segin
 */

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly.
}

// Include admin functionality
require_once plugin_dir_path(__FILE__) . 'fetch_recipes_admin.php';

// Schedule event on plugin activation.
function fr_activate_plugin() {
    if (!wp_next_scheduled('fr_fetch_recipes_event')) {
        wp_schedule_event(time(), 'hourly', 'fr_fetch_recipes_event');
    }
    // Run immediately on activation
    fr_fetch_and_create_recipes();
}
register_activation_hook(__FILE__, 'fr_activate_plugin');

// Clear scheduled event on plugin deactivation.
function fr_deactivate_plugin() {
    wp_clear_scheduled_hook( 'fr_fetch_recipes_event' );
}
register_deactivation_hook( __FILE__, 'fr_deactivate_plugin' );

// Hook our function into the event.
add_action( 'fr_fetch_recipes_event', 'fr_fetch_and_create_recipes' );

/**
 * Main Logic: Fetch recipes from Django API and create/update WP Delicious recipes.
 */
function fr_fetch_and_create_recipes() {
    // Initialize results tracking
    $results = array(
        'created' => 0,
        'updated' => 0,
        'errors' => 0
    );

    error_log('=== STARTING RECIPE FETCH PROCESS ===');

    // API Endpoint (Adjust to 'http://web:8000/api/recipes/' if using Docker networking)
    $api_url = 'http://localhost:8000/api/recipes/';
    // $api_url = 'http://web:8000/api/recipes/'; // Uncomment for Docker internal network

    error_log('Attempting to fetch recipes from: ' . $api_url);

    // Use WP HTTP API to fetch data.
    $response = wp_remote_get($api_url, array(
        'timeout' => 30,
        'sslverify' => false // Disable SSL verification for development
    ));

    if (is_wp_error($response)) {
        error_log('Fetch Recipes ERROR: ' . $response->get_error_message());
        return false;
    }

    $body = wp_remote_retrieve_body($response);
    $recipes = json_decode($body, true);

    if (empty($recipes) || !is_array($recipes)) {
        error_log('Fetch Recipes ERROR: Invalid JSON response.');
        return false;
    }

    error_log('Successfully parsed JSON. Found ' . count($recipes) . ' recipes');

    // Loop through each recipe
    foreach ($recipes as $index => $recipe) {
        // Skip recipes without ID
        $recipe_id = isset($recipe['id']) ? $recipe['id'] : null;
        if (!$recipe_id) continue;

        error_log('Processing recipe ID: ' . $recipe_id . ', Title: ' . (isset($recipe['title']) ? $recipe['title'] : 'Unknown'));

        // Check if a recipe with this unique identifier exists
        // Note: WP Delicious uses 'recipe' post type
        $existing_posts = new WP_Query(array(
            'post_type'  => 'recipe',
            'meta_key'   => 'fr_recipe_id',
            'meta_value' => $recipe_id,
            'fields'     => 'ids'
        ));

        // Map the API data to WP Delicious structure
        $delicious_meta = fr_map_recipe_to_delicious_meta($recipe);
        $post_title = isset($recipe['title']) ? $recipe['title'] : 'Untitled Recipe';

        // POPRAWKA 1: Wypełniamy post_content opisem przepisu
        // Używamy opisu z API, a jeśli go brak, generujemy prosty tekst.
        $post_content = isset($recipe['description']) ? $recipe['description'] : '';
        if (empty($post_content)) {
            $post_content = 'Przepis wygenerowany automatycznie.';
        }
        // Opcjonalnie: opakuj w paragrafy, jak robi to Gutenberg
        $post_content = '<p>' . nl2br($post_content) . '</p>';

        $post_data = array(
            'post_title'   => wp_strip_all_tags($post_title),
            'post_content' => $post_content,
            'post_status'  => 'draft',
            'post_author'  => 1,
            'post_type'    => 'recipe', // Required for WP Delicious
            'post_date'    => current_time('mysql') // Set current local time
        );

        // Update or Insert logic
        if ($existing_posts->have_posts()) {
            // --- UPDATE EXISTING ---
            $post_id = $existing_posts->posts[0];

            // Check timestamps
            $last_updated = get_post_meta($post_id, 'fr_recipe_updated_at', true);
            $recipe_updated = isset($recipe['updated_at']) ? $recipe['updated_at'] : '';

            if (empty($last_updated) || empty($recipe_updated) || $recipe_updated > $last_updated) {
                error_log('Updating existing recipe ID: ' . $post_id);

                $post_data['ID'] = $post_id;
                $update_result = wp_update_post($post_data, true);

                if (is_wp_error($update_result)) {
                    error_log('Error updating post: ' . $update_result->get_error_message());
                    $results['errors']++;
                } else {
                    // Update metadata
                    fr_update_recipe_meta($post_id, $delicious_meta, $recipe_id, $recipe_updated);

                    // Update image
                    if (isset($recipe['image_url']) && !empty($recipe['image_url'])) {
                        fr_set_featured_image($post_id, $recipe['image_url']);
                    }
                    $results['updated']++;
                }
            } else {
                error_log('Recipe is up to date, skipping update');
            }
        } else {
            // --- INSERT NEW ---
            error_log('Creating new recipe for ID: ' . $recipe_id);

            $post_id = wp_insert_post($post_data, true);

            if (is_wp_error($post_id)) {
                error_log('Error creating post: ' . $post_id->get_error_message());
                $results['errors']++;
            } else {
                error_log('New recipe created successfully with ID: ' . $post_id);

                // Save metadata
                fr_update_recipe_meta($post_id, $delicious_meta, $recipe_id, isset($recipe['updated_at']) ? $recipe['updated_at'] : '');

                // Set featured image
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
 * Helper function to update all required post meta
 */
function fr_update_recipe_meta($post_id, $delicious_meta, $api_id, $api_updated_at) {
    // 1. Main WP Delicious data blob
    update_post_meta($post_id, 'delicious_recipes_metadata', $delicious_meta);

    // 2. Helper fields for filtering/sorting in admin
    update_post_meta($post_id, '_dr_difficulty_level', 'beginner');
    update_post_meta($post_id, '_dr_best_season', 'summer');

    // POPRAWKA 2: Generowanie listy składników (_dr_recipe_ingredients)
    // Wtyczka wymaga prostej tablicy z nazwami składników
    $simple_ingredients = array();
    $ing_count = 0;

    if (!empty($delicious_meta['recipeIngredients'][0]['ingredients'])) {
        $ingredients_raw = $delicious_meta['recipeIngredients'][0]['ingredients'];
        $ing_count = count($ingredients_raw);

        foreach ($ingredients_raw as $ing_item) {
            // Pobieramy samą nazwę składnika
            if (!empty($ing_item['ingredient'])) {
                $simple_ingredients[] = $ing_item['ingredient'];
            }
        }
    }

    update_post_meta($post_id, '_dr_ingredient_count', $ing_count);
    // Zapisujemy tę listę - to kluczowe, czego brakowało w porównaniu do ID 108
    update_post_meta($post_id, '_dr_recipe_ingredients', $simple_ingredients);

    // 3. Synchronizacja
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

    // Parse Ingredients
    if (preg_match('/#\s*Ingredients(.*?)(?=#|$)/s', $raw_instructions, $m)) {
        $lines = preg_split('/^\s*-\s*/m', trim($m[1]), -1, PREG_SPLIT_NO_EMPTY);
        foreach ($lines as $line) {
            // Simplified parsing: putting everything in 'ingredient' field
            // WP Delicious expects: quantity, unit, ingredient, notes
            $ingredients_list[] = [
                'quantity' => '',
                'unit' => '',
                'ingredient' => trim($line),
                'notes' => ''
            ];
        }
    }

    // Parse Instructions
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

    // Extract Times
    $prep_time = '15';
    $cook_time = '15';
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

        // Required empty arrays to prevent errors
        'imageGalleryImages'=> [],
        'videoGalleryVids'  => []
    ];
}

/**
 * Set featured image for a post from URL
 */
function fr_set_featured_image($post_id, $image_url) {
    if (has_post_thumbnail($post_id)) {
        return;
    }

    require_once(ABSPATH . 'wp-admin/includes/media.php');
    require_once(ABSPATH . 'wp-admin/includes/file.php');
    require_once(ABSPATH . 'wp-admin/includes/image.php');

    $tmp = download_url($image_url);
    if (is_wp_error($tmp)) {
        error_log('Error downloading image: ' . $tmp->get_error_message());
        return false;
    }

    $file_array = array(
        'name' => basename($image_url),
        'tmp_name' => $tmp
    );

    $attachment_id = media_handle_sideload($file_array, $post_id);

    if (is_wp_error($attachment_id)) {
        @unlink($tmp);
        error_log('Error saving image: ' . $attachment_id->get_error_message());
        return false;
    }

    set_post_thumbnail($post_id, $attachment_id);
    return true;
}