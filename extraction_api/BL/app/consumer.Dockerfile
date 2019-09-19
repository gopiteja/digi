FROM apache_base

# Sets the working directory for following COPY and CMD instructions
# Notice we haven’t created a directory by this name - this
# instruction creates a directory with this name if it doesn’t exist
WORKDIR /app

# Copy rest of the files
COPY . /app/

# Run yourr_api.py when the container launches
# CMD ["python", "-u", "detection_app.py", "-p", "5008"]
CMD ["python", "-u", "consumer.py"]