FROM ghcr.io/ggml-org/llama.cpp:server-intel

# O modelo GGUF será montado via volume
EXPOSE 8080

# llama-server com API compatível OpenAI
# --host 0.0.0.0: escuta em todas as interfaces
# --port 8080: porta do servidor
# --n-gpu-layers 99: offload máximo para GPU
# O modelo é passado via variável de ambiente ou argumento
ENTRYPOINT ["/app/llama-server"]
CMD ["--host", "0.0.0.0", "--port", "8080", "--n-gpu-layers", "99"]
