FROM ubuntu:24.04 AS cardano-builder

WORKDIR /root/src

# Install dependencies
RUN apt update --fix-missing \
    && apt install -y --no-install-recommends \
        automake build-essential pkg-config libffi-dev libgmp-dev libssl-dev libncurses-dev libsystemd-dev zlib1g-dev make \
        g++ tmux git jq wget libncursesw5-dev libtool autoconf liblmdb-dev curl ca-certificates \
    && apt-get clean

# Install ghcup
ENV BOOTSTRAP_HASKELL_NONINTERACTIVE=1
RUN bash -c "curl --proto '=https' --tlsv1.2 -sSf https://get-ghcup.haskell.org | sh"

ENV PATH=/root/.local/bin:/root/.ghcup/bin:/root/.cabal/bin:${PATH}

ARG BLST_VERSION="0.3.11"
ARG LIBSODIUM_VERSION="dbb48cc"
ARG SECP256K1_VERSION="ac83be33"

ARG CABAL_VERSION=${CABAL_VERSION:-3.12.1.0}
ARG GHC_VERSION=${GHC_VERSION:-9.6.7}

ARG CARDANO_NODE_VERSION=${CARDANO_NODE_VERSION:-10.3.1}

RUN bash -c "ghcup install cabal ${CABAL_VERSION}"
RUN bash -c "ghcup set cabal ${CABAL_VERSION}"

RUN bash -c "ghcup install ghc ${GHC_VERSION}"
RUN bash -c "ghcup set ghc ${GHC_VERSION}"

WORKDIR /usr/local/src

# Install sodium
RUN git clone --branch master https://github.com/IntersectMBO/libsodium.git \
 && cd libsodium \
 && git checkout ${LIBSODIUM_VERSION} \
 && \
    for i in $(seq 1 10); do \
      echo "Attempt $i/10: building libsodium…"; \
      if ./autogen.sh && ./configure && make && make check && make install; then \
        echo "Success on attempt $i"; \
        break; \
      elif [ "$i" -eq 10 ]; then \
        echo "All 10 attempts failed, aborting" >&2; \
        exit 1; \
      else \
        echo "Build failed, retrying in 10s…"; \
        sleep 10; \
      fi; \
    done

# Install secp256k1
RUN git clone --branch master https://github.com/bitcoin-core/secp256k1.git \
 && cd secp256k1 \
 && git checkout ${SECP256K1_VERSION} \
 && \
    for i in $(seq 1 10); do \
      echo "Attempt $i/10: building secp256k1…"; \
      if ./autogen.sh \
         && ./configure --prefix=/usr --enable-module-schnorrsig --enable-experimental \
         && make \
         && make check \
         && make install; then \
        echo "secp256k1 built successfully on attempt $i"; \
        break; \
      elif [ "$i" -eq 10 ]; then \
        echo "All 10 attempts failed for secp256k1, aborting." >&2; \
        exit 1; \
      else \
        echo "Build failed on attempt $i — retrying in 10s…"; \
        sleep 10; \
      fi; \
    done

# Install blst
RUN git clone --branch master https://github.com/supranational/blst.git \
 && cd blst \
 && git checkout v${BLST_VERSION} \
 && \
    for i in $(seq 1 10); do \
      echo "Attempt $i/10: building blst…"; \
      if ./build.sh \
        && echo "prefix=/usr/local" >> libblst.pc \
        && echo "exec_prefix=\${prefix}" >> libblst.pc \
        && echo "libdir=\${exec_prefix}/lib" >> libblst.pc \
        && echo "includedir=\${prefix}/include" >> libblst.pc \
        && echo "" >> libblst.pc \
        && echo "Name: libblst" >> libblst.pc \
        && echo "Description: Multilingual BLS12-381 signature library" >> libblst.pc \
        && echo "URL: https://github.com/supranational/blst" >> libblst.pc \
        && echo "Version: ${BLST_VERSION#v}" >> libblst.pc \
        && echo "Cflags: -I\${includedir}" >> libblst.pc \
        && echo "Libs: -L\${libdir} -lblst" >> libblst.pc \
        && cp libblst.pc /usr/local/lib/pkgconfig/ \
        && cp bindings/blst_aux.h bindings/blst.h bindings/blst.hpp  /usr/local/include/ \
        && cp libblst.a /usr/local/lib \
        && bash -c "chmod u=rw,go=r /usr/local/{lib/{libblst.a,pkgconfig/libblst.pc},include/{blst.{h,hpp},blst_aux.h}}"; then \
        echo "blst built successfully on attempt $i"; \
        break; \
      elif [ "$i" -eq 10 ]; then \
        echo "All 10 attempts failed for blst, aborting." >&2; \
        exit 1; \
      else \
        echo "blst build failed on attempt $i — retrying in 10s…"; \
        sleep 10; \
      fi; \
    done

# Install cardano-node
RUN git clone https://github.com/intersectmbo/cardano-node.git \
    && cd cardano-node \
    && git checkout tags/${CARDANO_NODE_VERSION} \
    && echo "with-compiler: ghc-${GHC_VERSION}" >> cabal.project.local \
    && echo "" >> cabal.project.local \
    && echo "package cardano-crypto-praos" >> cabal.project.local \
    && echo "  flags: -external-libsodium-vrf" >> cabal.project.local \
    && echo "" >> cabal.project.local \
    && echo "package trace-dispatcher" >> cabal.project.local \
    && echo "  ghc-options: -Wwarn" >> cabal.project.local \
    && echo "" >> cabal.project.local \
    && echo "package HsOpenSSL" >> cabal.project.local \
    && echo "  flags: -homebrew-openssl" >> cabal.project.local \
    && echo "" >> cabal.project.local \
    && mkdir -p /usr/local/opt/openssl \
    && ln -s /opt/homebrew/opt/openssl@3/lib /usr/local/opt/openssl/lib \
    && ln -s /opt/homebrew/opt/openssl@3/include /usr/local/opt/openssl/include

WORKDIR /usr/local/src/cardano-node

RUN bash -c "cabal update"
RUN bash -c "cabal build all"
RUN bash -c "cabal build cardano-cli"
RUN bash -c "cabal build cardano-submit-api"

RUN mkdir -p /root/.local/bin \
    && cp -p "$(./scripts/bin-path.sh cardano-node)" /root/.local/bin/ \
    && cp -p "$(./scripts/bin-path.sh cardano-cli)" /root/.local/bin/ \
    && cp -p "$(./scripts/bin-path.sh cardano-submit-api)" /root/.local/bin/


FROM ubuntu:24.04 AS node-runner
COPY --from=cardano-builder /usr/local/lib /usr/local/lib
COPY --from=cardano-builder /root/.local/bin/cardano-* /usr/local/bin/
COPY --from=cardano-builder /usr/local/src/cardano-node/cardano-submit-api/config/tx-submit-mainnet-config.yaml /cardano-submit-api-config/cardano-submit-api.yaml

# Link libsodium library
COPY --from=cardano-builder --chown=root:root /usr/local/lib/libsodium.so /usr/local/lib
RUN ln -snf /usr/local/lib/libsodium.so /usr/local/lib/libsodium.so.23 \
    && ln -snf /usr/local/lib/libsodium.so /usr/local/lib/libsodium.so.23.3.0
RUN ldconfig

# Link secp256k1 library
COPY --from=cardano-builder --chown=root:root /usr/local/src/secp256k1/.libs/libsecp256k1.so /usr/local/lib
RUN ln -snf /usr/local/lib/libsecp256k1.so /usr/local/lib/libsecp256k1.so.0 \
    && ln -snf /usr/local/lib/libsecp256k1.so /usr/local/lib/libsecp256k1.so.1 \
    && ln -snf /usr/local/lib/libsecp256k1.so /usr/local/lib/libsecp256k1.so.1.0.1
RUN ldconfig

ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
ENV PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH

RUN mkdir /logs

COPY ./docker/dockerfiles/node/entrypoint.sh /sbin/entrypoint.sh
RUN chmod +x /sbin/entrypoint.sh

ENTRYPOINT ["/sbin/entrypoint.sh"]
