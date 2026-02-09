<?php
/**
 * Add admin menu for recipe fetching
 */
// Add this at the top of fetch_recipes_admin.php
add_action('admin_notices', function() {
    echo '<div class="notice notice-success"><p>Fetch Recipes admin file loaded successfully!</p></div>';
});

function fr_add_admin_menu() {
    add_management_page(
        'Fetch Recipes',
        'Fetch Recipes',
        'manage_options',
        'fetch_recipes',
        'fr_admin_page'
    );
}
add_action('admin_menu', 'fr_add_admin_menu');

/**
 * Admin page callback
 */
function fr_admin_page() {
    // Check if the form is submitted
    if (isset($_POST['fr_fetch_now']) && check_admin_referer('fr_fetch_recipes_nonce')) {
        // Call the fetch function
        $result = fr_fetch_and_create_recipes();
        
        if ($result) {
            echo '<div class="notice notice-success is-dismissible"><p>Recipes fetched successfully! ' . $result['created'] . ' recipes created and ' . $result['updated'] . ' recipes updated.</p></div>';
        } else {
            echo '<div class="notice notice-error is-dismissible"><p>Failed to fetch recipes. Check error log for details.</p></div>';
        }
    }
    ?>
    <div class="wrap">
        <h1>Fetch Recipes from API</h1>
        <p>Use this button to manually fetch recipes from the API immediately.</p>
        <form method="post">
            <?php wp_nonce_field('fr_fetch_recipes_nonce'); ?>
            <input type="submit" name="fr_fetch_now" class="button button-primary" value="Fetch Recipes Now">
        </form>
        
        <h2>Last Run Information</h2>
        <p>Last fetch: <?php echo get_option('fr_last_fetch_time') ? date('Y-m-d H:i:s', get_option('fr_last_fetch_time')) : 'Never'; ?></p>
        <p>Next scheduled run: <?php echo wp_next_scheduled('fr_fetch_recipes_event') ? date('Y-m-d H:i:s', wp_next_scheduled('fr_fetch_recipes_event')) : 'Not scheduled'; ?></p>
    </div>
    <?php
}
