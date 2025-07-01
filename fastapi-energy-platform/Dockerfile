# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /code

# Copy the requirements file into the container at /code
COPY ./requirements.txt /code/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of the application's code into the container at /code
COPY ./app /code/app
COPY ./models /code/models # If you have a separate top-level models dir for ML

# Make port 80 available to the world outside this container
EXPOSE 80

# Run main.py when the container launches
# Use uvicorn to run the FastAPI application
# The host 0.0.0.0 makes the app accessible from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
