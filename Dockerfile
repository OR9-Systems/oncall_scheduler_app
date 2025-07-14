# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /oncall_scheduler

# Copy the current directory contents into the container at /oncall_scheduler
COPY . /oncall_scheduler

ENV TZ=America/Toronto

RUN apt-get update && \
    apt-get install -y cron nano tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get clean
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r /oncall_scheduler/requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=run.py
# Run the application
#CMD ["tail", "-f", "/dev/null"]
CMD cd oncall_scheduler && flask run --host=0.0.0.0