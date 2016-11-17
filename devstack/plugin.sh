# zun - Devstack extras script to install zun

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "zun's plugin.sh was called..."
source $DEST/zun/devstack/lib/zun
source $DEST/zun/devstack/lib/nova
(set -o posix; set)

if is_service_enabled zun-api zun-compute; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing zun"
        install_docker
        install_zun

        LIBS_FROM_GIT="${LIBS_FROM_GIT},python-zunclient"
        install_zunclient
        cleanup_zun

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring zun"
        configure_zun

        if is_service_enabled key; then
            create_zun_accounts
        fi

        if [[ ${ZUN_DRIVER} == "nova-docker" ]]; then
            configure_nova_docker
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize zun
        init_zun

        # Start the zun API and zun compute
        echo_summary "Starting zun"
        start_zun
        upload_sandbox_image

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
