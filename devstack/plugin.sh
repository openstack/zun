# zun - Devstack extras script to install zun

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "zun's plugin.sh was called..."
source $DEST/zun/devstack/lib/zun
(set -o posix; set)

if is_service_enabled zun-api zun-compute; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing zun"
        install_zun

        install_zunclient
        cleanup_zun

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring zun"
        configure_zun

        if is_service_enabled key; then
            create_zun_accounts
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize zun
        init_zun

        # Start the zun API and zun compute
        echo_summary "Starting zun"
        start_zun
        upload_images

    fi

    if [[ "$1" == "unstack" ]]; then
        stop_zun
    fi

    if [[ "$1" == "clean" ]]; then
        cleanup_zun
    fi
fi

# Restore xtrace
$XTRACE
