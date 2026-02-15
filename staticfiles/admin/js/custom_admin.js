/**
 * RoomBooker Premium Admin - Custom JS
 * Handles advanced UI interactions like the premium sidebar toggle.
 */

$(document).ready(function() {
    // Synchronizacja po załadowaniu strony
    if ($('body').hasClass('sidebar-collapse')) {
        $('.main-sidebar').css('margin-left', '-280px');
        $('.content-wrapper, .main-header, .main-footer').css('margin-left', '0');
    }

    // Obsługa kliknięcia hamburgera (PushMenu)
    $('[data-widget="pushmenu"]').on('collapsed.lte.pushmenu', function() {
        // Sidebar się schował - upewniamy się że całkiem
        console.log('Sidebar collapsed');
        // CSS w custom_admin.css załatwia resztę dzięki klasie .sidebar-collapse
    });

    $('[data-widget="pushmenu"]').on('shown.lte.pushmenu', function() {
        // Sidebar się pokazał
        console.log('Sidebar shown');
    });
});
