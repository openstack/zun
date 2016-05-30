# higgins - Devstack extras script to install higgins

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "higgins's plugin.sh was called..."
source $DEST/higgins/devstack/lib/higgins
(set -o posix; set)

if is_service_enabled higgins-api higgins-conductor; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing higgins"
        install_higgins

	# TODO
        # LIBS_FROM_GIT="${LIBS_FROM_GIT},python-higginsclient"
        # install_higginsclient

        cleanup_higgins
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring higgins"
        configure_higgins

        if is_service_enabled key; then
            create_higgins_accounts
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize higgins
        init_higgins

        # Start the higgins API and higgins conductor
        echo_summary "Starting higgins"
        start_higgins

    fi

    if [[ "$1" == "unstack" ]]; then
        stop_higgins
    fi

    if [[ "$1" == "clean" ]]; then
        cleanup_higgins
    fi
fi

# Restore xtrace
$XTRACE
