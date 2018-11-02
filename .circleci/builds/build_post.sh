#!/bin/bash

set -ex

# report sccache hit/miss stats
if hash sccache 2>/dev/null; then
    sccache --show-stats
fi
