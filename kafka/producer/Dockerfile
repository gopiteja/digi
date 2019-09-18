FROM apache_base

# The EXPOSE instruction indicates the ports on which a container # # will listen for connections
# Since Flask apps listen to port 5002  by default, we expose it
EXPOSE 6969

# Sets the working directory for following COPY and CMD instructions
# Notice we haven’t created a directory by this name - this
# instruction creates a directory with this name if it doesn’t exist
WORKDIR /app

COPY . /app/

# Run app.py when the container launches
CMD ["python", "-u", "producer.py", "-p", "6969"]
