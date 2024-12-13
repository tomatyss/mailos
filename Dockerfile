FROM python:3.13-slim

# Install mailos package
RUN pip install mailos

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD ["mailos"]
