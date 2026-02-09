<?php
/**
 * Plugin Name: Fetch Recipes from API
 * Description: Periodically fetches new recipes from a Django API and creates WordPress posts as drafts.
 * Version: 1.1
 * Author: Your Name
 */

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly.
}

// Include admin functionality (moved after ABSPATH check)
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
 * Fetch recipes from Django API and create WordPress posts.
 */
function fr_fetch_and_create_recipes() {
    // Initialize results tracking
    $results = array(
        'created' => 0,
        'updated' => 0,
        'errors' => 0
    );
    
    error_log('=== STARTING RECIPE FETCH PROCESS ===');
    
    // Set your API endpoint URL (adjust the URL and parameters as needed).
    $api_url = 'http://localhost:8000/api/recipes/';
    error_log('Attempting to fetch recipes from: ' . $api_url);
    
    // Use WP HTTP API to fetch data.
    error_log('Sending API request...');
    $response = wp_remote_get($api_url, array(
        'timeout' => 30,     // Increased timeout
        'sslverify' => false // Disable SSL verification for testing
    ));
    
    if (is_wp_error($response)) {
        error_log('Fetch Recipes ERROR: ' . $response->get_error_message());
        return false;
    }
    
    // Log response details
    $status_code = wp_remote_retrieve_response_code($response);
    error_log('API response status code: ' . $status_code);
    
    $body = wp_remote_retrieve_body($response);
    error_log('API response body (first 200 chars): ' . substr($body, 0, 200) . '...');
    
    // Parse JSON
    error_log('Attempting to parse JSON response...');
    $recipes = json_decode($body, true);
    
    if (empty($recipes) || !is_array($recipes)) {
        error_log('Fetch Recipes ERROR: Invalid JSON response. Full response: ' . $body);
        return false;
    }
    
    error_log('Successfully parsed JSON. Found ' . count($recipes) . ' recipes');
    
    // Loop through each recipe and create a new post if it doesn't exist.
    foreach ($recipes as $index => $recipe) {
        error_log('Processing recipe ' . ($index + 1) . ' of ' . count($recipes));
        
        // Skip recipes without ID
        $recipe_id = isset($recipe['id']) ? $recipe['id'] : null;
        if (!$recipe_id) {
            error_log('Skipping recipe without ID');
            continue;
        }
        
        error_log('Processing recipe ID: ' . $recipe_id . ', Title: ' . (isset($recipe['title']) ? $recipe['title'] : 'Unknown'));
        
        // Check if a post with this unique identifier exists
        $existing_posts = new WP_Query(array(
            'post_type'  => 'post',
            'meta_key'   => 'fr_recipe_id',
            'meta_value' => $recipe_id,
            'fields'     => 'ids'
        ));
        
        $post_title = isset($recipe['title']) ? $recipe['title'] : 'Untitled Recipe';
        
        try {
            error_log('Formatting recipe content...');
            $post_content = fr_format_recipe_content($recipe);
            error_log('Content formatting successful');
        } catch (Exception $e) {
            error_log('Error formatting recipe content: ' . $e->getMessage());
            $results['errors']++;
            continue;
        }
        
        if ($existing_posts->have_posts()) {
            // Update existing post if needed
            $post_id = $existing_posts->posts[0];
            error_log('Found existing post ID: ' . $post_id . ' for recipe ID: ' . $recipe_id);
            
            // Get the last update time from post meta
            $last_updated = get_post_meta($post_id, 'fr_recipe_updated_at', true);
            $recipe_updated = isset($recipe['updated_at']) ? $recipe['updated_at'] : '';
            
            error_log('Last update time: ' . ($last_updated ? $last_updated : 'never') . 
                      ', Recipe updated at: ' . ($recipe_updated ? $recipe_updated : 'unknown'));
            
            // Only update if recipe has been modified (or if we don't have update timestamps)
            if (empty($last_updated) || empty($recipe_updated) || $recipe_updated > $last_updated) {
                error_log('Updating existing post...');
                
                $update_result = wp_update_post(array(
                    'ID' => $post_id,
                    'post_title' => wp_strip_all_tags($post_title),
                    'post_content' => $post_content
                ), true);
                
                if (is_wp_error($update_result)) {
                    error_log('Error updating post: ' . $update_result->get_error_message());
                    $results['errors']++;
                } else {
                    error_log('Post updated successfully');
                    $results['updated']++;
                    
                    // Update the last updated timestamp
                    if (!empty($recipe_updated)) {
                        update_post_meta($post_id, 'fr_recipe_updated_at', $recipe_updated);
                    }
                    
                    // Update featured image if needed
                    if (isset($recipe['image_url']) && !empty($recipe['image_url'])) {
                        error_log('Setting featured image: ' . $recipe['image_url']);
                        fr_set_featured_image($post_id, $recipe['image_url']);
                    }
                }
            } else {
                error_log('Post is already up to date, skipping update');
            }
        } else {
            // Insert a new post as draft
            error_log('Creating new post for recipe ID: ' . $recipe_id);
            
            $post_data = array(
                'post_title'   => wp_strip_all_tags($post_title),
                'post_content' => $post_content,
                'post_status'  => 'draft',
                'post_author'  => 1, // Adjust author ID as needed
                'post_type'    => 'post'
            );
            
            $post_id = wp_insert_post($post_data, true);
            
            if (is_wp_error($post_id)) {
                error_log('Error creating post: ' . $post_id->get_error_message());
                $results['errors']++;
            } else {
                error_log('New post created successfully with ID: ' . $post_id);
                $results['created']++;
                
                // Save recipe metadata
                update_post_meta($post_id, 'fr_recipe_id', $recipe_id);
                
                if (isset($recipe['updated_at']) && !empty($recipe['updated_at'])) {
                    update_post_meta($post_id, 'fr_recipe_updated_at', $recipe['updated_at']);
                }
                
                // Set featured image if available
                if (isset($recipe['image_url']) && !empty($recipe['image_url'])) {
                    error_log('Setting featured image: ' . $recipe['image_url']);
                    fr_set_featured_image($post_id, $recipe['image_url']);
                }
            }
        }
    }
    
    // Store the last run time
    update_option('fr_last_fetch_time', time());
    
    error_log('=== RECIPE FETCH COMPLETE ===');
    error_log('Results: Created: ' . $results['created'] . ', Updated: ' . $results['updated'] . ', Errors: ' . $results['errors']);
    
    return $results;
}

/**
 * Format recipe content with proper HTML structure and Schema.org markup
 */
function fr_format_recipe_content($recipe) {
    $post_content = '<div class="recipe-container">';

    // Add description
    if (isset($recipe['description']) && !empty($recipe['description'])) {
        $post_content .= '<div class="recipe-description">' . wp_kses_post($recipe['description']) . '</div>';
    }

    // Extract recipe sections
    $ingredients = array();
    $steps = array();
    $nutrition = '';
    $prep_time = '';
    $cook_time = '';

    if (isset($recipe['instructions']) && !empty($recipe['instructions'])) {
        $instructions = $recipe['instructions'];

        // Extract ingredients
        if (preg_match('/#\s*Ingredients(.*?)(?=#|$)/s', $instructions, $ingredients_match)) {
            $ingredients_text = trim($ingredients_match[1]);
            $ingredients = preg_split('/^\s*-\s*/m', $ingredients_text, -1, PREG_SPLIT_NO_EMPTY);
            $ingredients = array_map('trim', $ingredients);
        }

        // Extract instructions
        if (preg_match('/#\s*Instructions(.*?)(?=#|$)/s', $instructions, $steps_match)) {
            $steps_text = trim($steps_match[1]);
            $steps = preg_split('/^\s*\d+\.\s*/m', $steps_text, -1, PREG_SPLIT_NO_EMPTY);
            $steps = array_map('trim', $steps);
        }

        // Extract nutritional information
        if (preg_match('/#\s*Nutritional Information(.*?)(?=#|$)/s', $instructions, $nutrition_match)) {
            $nutrition = trim($nutrition_match[1]);
        }

        // Extract times (only once)
        if (preg_match('/Prep Time:\s*(.*?)$/m', $instructions, $prep_match)) {
            $prep_time = trim($prep_match[1]);
        }
        if (preg_match('/Cook Time:\s*(.*?)$/m', $instructions, $cook_match)) {
            $cook_time = trim($cook_match[1]);
        }
    }

    // Time information at the top
    $time_info = '';
    if (!empty($prep_time) || !empty($cook_time)) {
        $post_content .= '<div class="recipe-time-info">';
        if (!empty($prep_time)) {
            $post_content .= '<span class="prep-time"><strong>Czas przygotowania:</strong> ' . $prep_time . '</span>';
        }
        if (!empty($cook_time)) {
            $post_content .= ' <span class="cook-time"><strong>Czas gotowania:</strong> ' . $cook_time . '</span>';
        }
        $post_content .= '</div>';
    }

    // Ingredients section
    if (!empty($ingredients)) {
        $post_content .= '<div class="recipe-ingredients">
                           <h3>Składniki</h3>
                           <ul>';
        foreach ($ingredients as $ingredient) {
            $post_content .= '<li>' . $ingredient . '</li>';
        }
        $post_content .= '</ul></div>';
    }

    // Instructions section
    if (!empty($steps)) {
        $post_content .= '<div class="recipe-steps">
                           <h3>Sposób przygotowania</h3>
                           <ol>';
        foreach ($steps as $step) {
            $post_content .= '<li>' . $step . '</li>';
        }
        $post_content .= '</ol></div>';
    }

    // Nutritional information
    if (!empty($nutrition)) {
        $post_content .= '<div class="recipe-nutrition">
                           <h3>Wartości odżywcze</h3>
                           <p>' . nl2br($nutrition) . '</p>
                           </div>';
    }

    // Close main container
    $post_content .= '</div>';

    // Add schema.org Recipe structured data
    $post_content .= fr_generate_recipe_schema($recipe, $ingredients, $steps, $prep_time, $cook_time);

    return $post_content;
}

/**
 * Generate Schema.org Recipe markup for better SEO
 */
function fr_generate_recipe_schema($recipe, $ingredients, $steps, $prep_time, $cook_time) {
    $title = isset($recipe['title']) ? $recipe['title'] : '';
    $description = isset($recipe['description']) ? $recipe['description'] : '';
    $image_url = isset($recipe['image_url']) ? $recipe['image_url'] : '';

    $schema = '<script type="application/ld+json">';
    $schema_data = array(
        '@context' => 'https://schema.org/',
        '@type' => 'Recipe',
        'name' => $title,
        'description' => $description,
        'author' => array(
            '@type' => 'Organization',
            'name' => get_bloginfo('name')
        ),
        'datePublished' => date('c')
    );

    // Add image if available
    if (!empty($image_url)) {
        $schema_data['image'] = $image_url;
    }

    // Add prep time if available
    if (!empty($prep_time)) {
        // Convert to ISO 8601 duration format if possible
        if (preg_match('/(\d+)\s*minutes/', $prep_time, $minutes_match)) {
            $schema_data['prepTime'] = 'PT' . $minutes_match[1] . 'M';
        } else {
            $schema_data['prepTime'] = $prep_time;
        }
    }

    // Add cook time if available
    if (!empty($cook_time)) {
        // Convert to ISO 8601 duration format if possible
        if (preg_match('/(\d+)\s*minutes/', $cook_time, $minutes_match)) {
            $schema_data['cookTime'] = 'PT' . $minutes_match[1] . 'M';
        } else {
            $schema_data['cookTime'] = $cook_time;
        }
    }

    // Add ingredients
    if (!empty($ingredients)) {
        $schema_data['recipeIngredient'] = $ingredients;
    }

    // Add instructions
    if (!empty($steps)) {
        $instructions = array();
        $step_number = 1;
        foreach ($steps as $step) {
            $instructions[] = array(
                '@type' => 'HowToStep',
                'text' => $step,
                'position' => $step_number++
            );
        }
        $schema_data['recipeInstructions'] = $instructions;
    }

    $schema .= json_encode($schema_data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    $schema .= '</script>';

    return $schema;
}

/**
 * Set featured image for a post from URL
 */
function fr_set_featured_image($post_id, $image_url) {
    // Check if this post already has a featured image
    if (has_post_thumbnail($post_id)) {
        return; // Don't override existing featured images
    }

    // Need to require these files
    require_once(ABSPATH . 'wp-admin/includes/media.php');
    require_once(ABSPATH . 'wp-admin/includes/file.php');
    require_once(ABSPATH . 'wp-admin/includes/image.php');

    // Download file to temp dir
    $tmp = download_url($image_url);
    if (is_wp_error($tmp)) {
        error_log('Error downloading image: ' . $tmp->get_error_message());
        return false;
    }

    // Prepare file data
    $file_array = array(
        'name' => basename($image_url),
        'tmp_name' => $tmp
    );

    // Move the temporary file into the uploads directory
    $attachment_id = media_handle_sideload($file_array, $post_id);

    // If error storing permanently, unlink
    if (is_wp_error($attachment_id)) {
        @unlink($tmp);
        error_log('Error saving image: ' . $attachment_id->get_error_message());
        return false;
    }

    // Set as featured image
    set_post_thumbnail($post_id, $attachment_id);

    return true;
}
