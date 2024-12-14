FROM python:3.13-slim

# Install mailos package with no cache and specific version
RUN pip install --no-cache-dir mailos>=0.1.2

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD ["mailos"]
