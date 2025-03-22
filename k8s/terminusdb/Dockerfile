FROM terminusdb/terminusdb-server:latest

# Set environment variables
ENV TERMINUSDB_SERVER_PORT=6363
ENV TERMINUSDB_ADMIN_PASS=root
ENV TERMINUSDB_AUTOLOGIN=true

# Expose the TerminusDB port
EXPOSE 6363

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:6363/api/ || exit 1

# Set default command
CMD ["/startup.sh"] 