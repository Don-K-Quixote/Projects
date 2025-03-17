# Use Python as base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the app files into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8050 for the Dash app
EXPOSE 8050

# Command to run the app
CMD ["python", "app.py"]
