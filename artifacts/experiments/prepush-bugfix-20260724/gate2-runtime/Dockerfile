# Gate 2 runtime image — pinned validators for the pre-push Bug Fix pilot.
#
# Build phase MAY use the network (that is where downloads are hash-verified).
# Runtime MUST be: --network none, --read-only, non-root, with only an isolated
# writable volume. It must NOT mount the framework repo, the raw bundle, or the
# Docker socket.
#
# This image contains validators ONLY. Arm packets are mounted read-only per arm
# at run time; they are deliberately NOT baked in, so one image cannot leak a
# treatment across arms.
FROM python:3.12-slim-bookworm

ARG SHELLCHECK_VERSION=0.10.0
ARG SHELLCHECK_SHA256=6c881ab0698e4e6ea235245f22832860544f17ba386442fe7e9d629f8cbedf87

# ShellCheck: download, verify sha256, install the static binary.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl xz-utils git; \
    rm -rf /var/lib/apt/lists/*; \
    curl -fsSL -o /tmp/sc.tar.xz \
      "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.x86_64.tar.xz"; \
    echo "${SHELLCHECK_SHA256}  /tmp/sc.tar.xz" | sha256sum -c -; \
    tar -xJf /tmp/sc.tar.xz -C /tmp; \
    install -m 0755 "/tmp/shellcheck-v${SHELLCHECK_VERSION}/shellcheck" /usr/local/bin/shellcheck; \
    rm -rf /tmp/sc.tar.xz "/tmp/shellcheck-v${SHELLCHECK_VERSION}"

# Python validators: hash-locked, no transitive resolution surprises.
COPY requirements.lock.txt /tmp/requirements.lock.txt
RUN set -eux; \
    pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock.txt; \
    rm -f /tmp/requirements.lock.txt

# Fail the build if any pin drifted.
RUN set -eux; \
    shellcheck --version | grep -q "version: ${SHELLCHECK_VERSION}"; \
    ruff --version | grep -q "0.6.9"; \
    mypy --version | grep -q "1.11.2"

# Non-root (UID 65532, the conventional "nonroot" id). Runtime uses --read-only,
# so the only writable location is the mounted workspace / tmpfs.
RUN groupadd -g 65532 nonroot && useradd -u 65532 -g 65532 -m -s /usr/sbin/nologin nonroot
USER 65532:65532
WORKDIR /work

# No ENTRYPOINT that could smuggle behavior; the runner passes an explicit command.
CMD ["/bin/sh", "-c", "shellcheck --version && ruff --version && mypy --version"]
