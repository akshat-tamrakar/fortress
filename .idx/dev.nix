# To learn more about how to use Nix to configure your environment
# see: https://firebase.google.com/docs/studio/customize-workspace
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-24.05"; # or "unstable"

  # Use https://search.nixos.org/packages to find packages
  packages = [
    # pkgs.go
    pkgs.python311
    # pkgs.python311Packages.pip
    # pkgs.nodejs_20
    # pkgs.nodePackages.nodemon
    pkgs.uv
  ];

  # Sets environment variables in the workspace
  env = {
    PYTHON_VERSION = "3.11";
  };
  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
      "ms-python.python"
      "charliermarsh.ruff"
    ];

    # Enable previews
    previews = {
      enable = true;
      previews = {
        # web = {
        #   # Example: run "npm run dev" with PORT set to IDX's defined port for previews,
        #   # and show it in IDX's web preview panel
        #   command = ["npm" "run" "dev"];
        #   manager = "web";
        #   env = {
        #     # Environment variables to set for your server
        #     PORT = "$PORT";
        #   };
        # };
      };
    };

    # Workspace lifecycle hooks
    workspace = {
      # Runs when a workspace is first created
      onCreate = {
        # Create virtual environment with UV
        create-venv = "uv venv";
        # Regenerate lock file to match current UV version
        regenerate-lock = "uv lock";
        # Install dependencies using UV (includes both regular and dev dependencies)
        install-deps = "uv sync";
      };
      # Runs when the workspace is (re)started
      onStart = {
        # Ensure lock file is up to date
        update-lock = "uv lock";
        # Sync dependencies
        sync-deps = "uv sync";
      };
    };
  };
}
