#!/bin/zsh

set -u

echo "Tico Asset Builder launcher"
echo "This only prepares the local project environment and opens the GUI."
echo "It does not touch ROM libraries or output folders."
echo ""

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || {
  echo "Could not open the project folder."
  echo "Press Return to close this window."
  read -r
  exit 1
}

PYTHON_CMD=""
for candidate in python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_CMD="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_CMD" ]]; then
  echo "Python 3 was not found. Please install Python 3.12 or newer, then try again."
  echo "Press Return to close this window."
  read -r
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  echo "Creating local Python environment..."
  "$PYTHON_CMD" -m venv .venv || {
    echo "Could not create .venv."
    echo "Press Return to close this window."
    read -r
    exit 1
  }
fi

source .venv/bin/activate || {
  echo "Could not activate .venv."
  echo "Press Return to close this window."
  read -r
  exit 1
}

echo "Updating installer tools..."
python -m pip install --upgrade pip || {
  echo "Could not update pip. Continuing with the current pip version."
}

echo "Installing Tico Asset Builder..."
if ! python -m pip install -e ".[modern-gui]"; then
  echo "Modern GUI dependencies could not be installed. Falling back to the stable GUI install."
  python -m pip install -e . || {
    echo "Could not install Tico Asset Builder."
    echo "Press Return to close this window."
    read -r
    exit 1
  }
fi

echo "Launching the GUI..."
if tico-asset-builder-modern-gui; then
  exit 0
fi

echo "Modern GUI did not start. Trying the stable GUI..."
if tico-asset-builder-gui; then
  exit 0
fi

echo ""
echo "Could not launch either GUI."
echo "On macOS, try opening Terminal in this folder and running:"
echo "  source .venv/bin/activate"
echo "  tico-asset-builder-gui"
echo ""
echo "Press Return to close this window."
read -r
exit 1
