#!/bin/bash
# Rename nb_uv_kernels -> nb_venv_kernels and nb-uv-kernels -> nb-venv-kernels

find . -type f \
    -not -path './.git/*' \
    -not -path './.yarn/*' \
    -not -path './node_modules/*' \
    -not -path './__pycache__/*' \
    -not -name '*.pyc' \
    -not -name 'rename_symbols.sh' \
    -exec grep -l -E 'nb_uv_kernels|nb-uv-kernels' {} \; | while read file; do
    echo "Processing: $file"
    sed -i 's/nb_uv_kernels/nb_venv_kernels/g' "$file"
    sed -i 's/nb-uv-kernels/nb-venv-kernels/g' "$file"
done

echo "Done."
