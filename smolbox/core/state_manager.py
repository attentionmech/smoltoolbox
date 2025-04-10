import json
import os
from datetime import datetime
from uuid import uuid4
import shutil

AUTORESOLVE = "<AUTO>"

ALLOWED_KEYS = [
    "model_path",
    "output_model_path",
    "dataset_path",
    "output_dataset_path",
]
WRITABLE_KEYS = ["output_model_path", "output_dataset_path"]


def is_colab():
    return os.path.exists("/content")


# Directory and file paths depending on environment
if is_colab():
    SMOLBOX_DIR = os.path.join("/content", ".smolbox")
else:
    SMOLBOX_DIR = os.path.join(os.getcwd(), ".smolbox")

STATE_FILE = os.path.join(SMOLBOX_DIR, "state.json")
STATE_HISTORY_FILE = os.path.join(SMOLBOX_DIR, "state_history.jsonl")


def now():
    return datetime.utcnow().isoformat() + "Z"


def ensure_smolbox_dir():
    if not os.path.exists(SMOLBOX_DIR):
        os.makedirs(SMOLBOX_DIR)

    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            json.dump({}, f)

def get_current_state():
    ensure_smolbox_dir()
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_current_state(state_dict):
    state_dict["updated_at"] = now()
    if "created_at" not in state_dict:
        state_dict["created_at"] = now()
    with open(STATE_FILE, "w") as f:
        json.dump(state_dict, f, indent=2, sort_keys=True)


def commit_history(state_dict=None):
    if state_dict is None:
        state_dict = get_current_state()
    with open(STATE_HISTORY_FILE, "a") as f:
        f.write(json.dumps(state_dict) + "\n")


def set(key, value) -> str:
    if key not in ALLOWED_KEYS:
        print(f"Invalid key name: {key} for state.")
    state = get_current_state()
    state[key] = value
    save_current_state(state)
    return value


def get(key, output=False) -> str:
    if key not in ALLOWED_KEYS:
        print(f"Invalid key name: {key} for state.")
    state = get_current_state()
    if output:
        print(state.get(key))
    return state.get(key)


def update_state(updates: dict):
    state = get_current_state()
    for k, v in updates.items():
        if k in ALLOWED_KEYS or k in ["created_at", "updated_at"]:
            state[k] = v
    save_current_state(state)


def resolve(key_name, key_value, write=False):
    dikt = get_current_state()

    if key_value != AUTORESOLVE:
        if key_value:
            dikt[key_name] = key_value
            save_current_state(dikt)
        return key_value

    if key_name not in ALLOWED_KEYS:
        print(f"Invalid key name: {key_name} for state.")
        raise ValueError(
            "Invalid key name for state. Allowed keys are: " + ", ".join(ALLOWED_KEYS)
        )

    if not write:
        if key_name in dikt and dikt[key_name] is not None:
            return dikt[key_name]
        else:
            raise ValueError(f"Could not resolve {key_name}")
    else:
        if key_name in WRITABLE_KEYS:
            if key_name in dikt and dikt[key_name] is not None:
                return dikt[key_name]
            else:
                new_folder_name = str(uuid4())
                new_folder_path = os.path.join(SMOLBOX_DIR, new_folder_name)
                os.makedirs(new_folder_path)

                dikt[key_name] = new_folder_path
                if "created_at" not in dikt:
                    dikt["created_at"] = now()
                dikt["updated_at"] = now()

                save_current_state(dikt)
                return new_folder_path


def next_state():
    current_state = get_current_state()
    commit_history(current_state)

    current_state["model_path"] = current_state.get(
        "output_model_path"
    ) or current_state.get("model_path")
    current_state["output_model_path"] = None

    current_state["dataset_path"] = current_state.get(
        "output_dataset_path"
    ) or current_state.get("dataset_path")
    current_state["output_dataset_path"] = None

    current_state["updated_at"] = now()

    save_current_state(current_state)
    return current_state


def reset_state():
    if os.path.exists(SMOLBOX_DIR):
        shutil.rmtree(SMOLBOX_DIR)


def init_state():
    reset_state()
    ensure_smolbox_dir()


def print_state():
    print(json.dumps(get_current_state(), indent=2))


def list_models():
    models_dir = os.path.join(SMOLBOX_DIR, "models")
    if not os.path.exists(models_dir):
        print("No models directory found.")
        return []

    models = [f for f in os.listdir(models_dir) if not f.startswith(".")]
    print("Available models:")
    for model in models:
        print(f"- {model}")
    return models
