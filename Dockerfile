# Use the official Azure Functions runtime image
FROM mcr.microsoft.com/azure-functions/python:4-python3.10

# Install Azure Functions Core Tools
RUN apt-get update && apt-get install -y wget gnupg
RUN wget -q https://packages.microsoft.com/config/debian/11/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y azure-functions-core-tools-4

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

COPY requirements.txt /
RUN pip install -r /requirements.txt

# Set the working directory to /home/site/wwwroot
WORKDIR /home/site/wwwroot

# Copy function_app.py and other necessary files to /home/site/wwwroot
COPY function_app.py /home/site/wwwroot
COPY additional_functions.py /home/site/wwwroot

# Copy the entire src directory to /home/site/wwwroot/src
COPY src /home/site/wwwroot/src