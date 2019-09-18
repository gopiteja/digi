FROM apache_base

# Sets the working directory for following COPY and CMD instructions
# Notice we haven’t created a directory by this name - this
# instruction creates a directory with this name if it doesn’t exist
WORKDIR /app

# Copy all files
COPY ./app /app/

# Run app
CMD ["python", "-u", "json_export.py"]
