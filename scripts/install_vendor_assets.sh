#!/bin/bash
set -euo pipefail

VENDOR_TMP=/tmp/pmketoan-vendor
mkdir -p static/vendor/css static/vendor/js static/vendor/fonts

# Strip sourceMappingURL references — WhiteNoise CompressedManifestStaticFilesStorage
# fails collectstatic if .map referenced but missing. Vendor files vendored không cần sourcemap.
strip_sourcemap() { sed -i 's|//# sourceMappingURL=[^ ]*||g' "$1"; }

# Install npm packages (no save, isolated)
rm -rf $VENDOR_TMP
mkdir -p $VENDOR_TMP
npm install --prefix $VENDOR_TMP --no-save \
    bootstrap@5.3.3 \
    bootstrap-icons@1.11.3 \
    htmx.org@2.0.0 \
    alpinejs@3.14.1

VENDOR=$VENDOR_TMP/node_modules
cp $VENDOR/bootstrap/dist/css/bootstrap.min.css static/vendor/css/
cp $VENDOR/bootstrap/dist/js/bootstrap.bundle.min.js static/vendor/js/ && strip_sourcemap static/vendor/js/bootstrap.bundle.min.js
cp $VENDOR/bootstrap-icons/font/bootstrap-icons.min.css static/vendor/css/
cp -r $VENDOR/bootstrap-icons/font/fonts/* static/vendor/fonts/
cp $VENDOR/htmx.org/dist/htmx.min.js static/vendor/js/ && strip_sourcemap static/vendor/js/htmx.min.js
cp $VENDOR/alpinejs/dist/cdn.min.js static/vendor/js/alpine.min.js && strip_sourcemap static/vendor/js/alpine.min.js

echo "✓ Vendor assets installed to static/vendor/"
