FROM apache_base

# The EXPOSE instruction indicates the ports on which a container
EXPOSE 6968

# Sets the working directory for following COPY and CMD instructions
# Notice we haven’t created a directory by this name - this
# instruction creates a directory with this name if it doesn’t exist
WORKDIR /app

COPY . /app/

# Run app.py when the container launches
CMD ["python", "-u", "consumer.py", "-p", "6968"]
