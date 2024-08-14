If there's an environment variable specifying the location of the Kubernetes configuration file, your Python script can be adapted to check for this environment variable first, and if it's not set, fall back to the default location (`~/.kube/config`). This approach allows users to customize the config file location while still supporting the standard location.

Here's how you can modify the script to handle an environment variable:

### Example Code

```python
import os
from kubernetes import client, config
from kubernetes.client.exceptions import ConfigException

def load_kube_config():
    # Check for an environment variable for the Kubernetes config path
    kube_config_path = os.getenv('KUBECONFIG')

    # If the environment variable is not set, fall back to the default path
    if not kube_config_path:
        kube_config_path = os.path.expanduser("~/.kube/config")

    # Check if the config file exists
    if not os.path.exists(kube_config_path):
        raise FileNotFoundError(f"Kubernetes config file not found at {kube_config_path}")

    try:
        # Load the Kubernetes config
        config.load_kube_config(config_file=kube_config_path)
        print("Kubernetes config loaded successfully")
    except ConfigException as e:
        raise ConfigException(f"Failed to load Kubernetes config: {str(e)}")

# Example usage
if __name__ == "__main__":
    try:
        load_kube_config()
        # Now you can use the Kubernetes API client
        v1 = client.CoreV1Api()
        print("Successfully connected to the Kubernetes API")
    except Exception as e:
        print(str(e))
```

### Explanation

1. **Environment Variable (`KUBECONFIG`):**
   - The script first checks for the environment variable `KUBECONFIG` using `os.getenv('KUBECONFIG')`.
   - If `KUBECONFIG` is set, it uses the path specified by this variable.
   - If `KUBECONFIG` is not set, it defaults to `~/.kube/config`.

2. **Path Handling:**
   - After determining the path (either from the environment variable or the default location), the script checks if the file exists and then attempts to load it.

### Usage

- **Setting the `KUBECONFIG` Environment Variable:**
  - You can set the `KUBECONFIG` environment variable in your shell before running the script:

    ```bash
    export KUBECONFIG=/path/to/your/custom/kubeconfig
    python your_script.py
    ```

- **Default Behavior:**
  - If the `KUBECONFIG` variable is not set, the script will automatically look for the config file at `~/.kube/config`.

This method ensures that your application can adapt to different user setups and environments, making it more versatile and user-friendly.
