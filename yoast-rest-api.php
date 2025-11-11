<?php

/*
Plugin Name: Yoast REST API fields
Description: Expose Yoast SEO title, meta description, and focus keyword via REST API
Version: 1.1
Author: Mamad
*/

/**
 * Add REST API support for Yoast Meta
 */
function register_yoast_meta_in_rest() {

    // Yoast meta description
    register_rest_field('post', 'yoast_description', array(
        'get_callback'    => function($post) {
            return get_post_meta($post['id'], '_yoast_wpseo_metadesc', true);
        },
        'update_callback' => function($value, $post) {
            update_post_meta($post->ID, '_yoast_wpseo_metadesc', sanitize_text_field($value));
        },
        'schema' => array(
            'type'        => 'string',
            'description' => 'Meta description for Yoast SEO',
        ),
    ));

    // Yoast focus keyword
    register_rest_field('post', 'yoast_keyword', array(
        'get_callback'    => function($post) {
            return get_post_meta($post['id'], '_yoast_wpseo_focuskw', true);
        },
        'update_callback' => function($value, $post) {
            update_post_meta($post->ID, '_yoast_wpseo_focuskw', sanitize_text_field($value));
        },
        'schema' => array(
            'type'        => 'string',
            'description' => 'Focus keyword for Yoast SEO',
        ),
    ));

    // Yoast SEO title
    register_rest_field('post', 'yoast_title', array(
        'get_callback'    => function($post) {
            return get_post_meta($post['id'], '_yoast_wpseo_title', true);
        },
        'update_callback' => function($value, $post) {
            update_post_meta($post->ID, '_yoast_wpseo_title', sanitize_text_field($value));
        },
        'schema' => array(
            'type'        => 'string',
            'description' => 'SEO title for Yoast',
        ),
    ));
}

add_action('rest_api_init', 'register_yoast_meta_in_rest');
