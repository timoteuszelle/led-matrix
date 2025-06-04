import subprocess

def get_sensors_data():
    result = subprocess.run(['sensors'], capture_output=True, text=True)
    return result.stdout

data = get_sensors_data()
print(data)