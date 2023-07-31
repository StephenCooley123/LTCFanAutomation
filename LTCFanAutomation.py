import smbus2
import bme280
import requests
import json
import requests
import json
import time
import os
import datetime

location = "01056"
port = 1
address = 0x76
api_key = "a500602bf5e44a7e8fc163526231807"
delay_time_minutes = 0.1
log_filename = "test_weather_log_1.log"


def main():
    bus = smbus2.SMBus(port)

    calibration_params = bme280.load_calibration_params(bus, address)
    while (1):
        calc_start_time = time.time()

        data = bme280.sample(bus, address, calibration_params)

        temperature_interior = data.temperature * 9 / 5 + 32
        humidity_interior = data.humidity
        hi_interior = str(heat_index(temperature_interior, humidity_interior))

        print(f"Interior Temperature: {temperature_interior:.2f} F")
        print(f"Interior Humidity: {humidity_interior:.2f} %")
        print("Interior Heat Index: " + hi_interior)

        data = get_weather_data(api_key)

        if data:
            localtime = data["location"]["localtime"]
            temp_f = data["current"]["temp_f"]
            humidity = data["current"]["humidity"]
            precip_in = data["current"]["precip_in"]
            precip_1hr_in = data["forecast"]["forecastday"][0]["hour"][0]["precip_in"]
            hi_exterior = str(heat_index(temp_f, humidity))
            print(f"Exterior Temperature temperature: {temp_f}°F")
            print(f"Exterior Humidity: {humidity}%")
            print(f"Exterior Precipitation: {precip_in} in")
            print(f"Exterior Precipitation 1h forecast: {precip_1hr_in} in")
            print("Exterior Heat Index: " + hi_exterior)

            set_fan_state(
                decide_outcome(heat_index(temperature_interior, humidity_interior), heat_index(temp_f, humidity),
                               precip_in, precip_1hr_in))
            log_data(log_filename, localtime, temperature_interior, humidity_interior, hi_interior, temp_f, humidity,
                     hi_exterior, precip_in, precip_1hr_in,
                     decide_outcome(heat_index(temperature_interior, humidity_interior), heat_index(temp_f, humidity),
                                    precip_in, precip_1hr_in))

        else:
            print("API Failure.")
            set_fan_state(0)
            current_time = datetime.datetime.now()
            log_data_error(log_filename, current_time, 0)

        calc_end_time = time.time()
        calc_time_elapsed = calc_end_time - calc_start_time
        time.sleep(delay_time_minutes * 60 - calc_time_elapsed)


def get_weather_data(api_key):
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q=" + location + "&days=1&aqi=no&alerts=no"
        response = requests.get(url)
        response.raise_for_status()
        return json.loads(response.text)
    except requests.exceptions.HTTPError as errh:
        print("HTTP Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        print("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        print("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        print("Something went wrong", err)


def log_data(filename, localtime, temperature_interior, humidity_interior, hi_interior, temp_f, humidity, hi_exterior,
             precip_in, precip_1hr_in, fan_state):
    text = str(localtime) + "\t" + str(temperature_interior) + "\t" + str(humidity_interior) + "\t" + str(
        hi_interior) + "\t" + str(temp_f) + "\t" + str(humidity) + "\t" + str(hi_exterior) + "\t" + str(
        precip_in) + "\t" + str(precip_1hr_in) + "\t" + str(fan_state)

    write_key = 0
    key = "localtime\ttemperature_interior\thumidity_interior\thi_interior\ttemp_exterior\thumidity_exterior\thi_exterior\tprecip\tprecip_1hr\tfan_state"

    if os.path.exists(filename):
        append_write = 'a'  # append if already exists

    else:
        append_write = 'w'  # make a new file if not
        write_key = 1
    f = open(filename, append_write)
    if (write_key):
        f.write(key + "\n")
    f.write(text + "\n")
    f.close()


def log_data_error(filename, localtime, api_state):
    text = str(localtime)
    write_key = 0
    key = "localtime\ttemperature_interior\thumidity_interior\thi_interior\ttemp_exterior\thumidity_exterior\thi_exterior\tprecip\tprecip_1hr\tfan_state"

    if os.path.exists(filename):
        append_write = 'a'  # append if already exists

    else:
        append_write = 'w'  # make a new file if not
        write_key = 1

    f = open(filename, append_write)
    if (write_key):
        f.write(key + "\n")
    f.write(text + "\n")
    f.close()


def heat_index(tempf, hum):
    # try simple formula first, if >80, do long formula
    hi = 0.5 * (tempf + 61.0 + ((tempf - 68.0) * 1.2) + (hum * 0.094))

    if (hi >= 80):

        C1 = [-42.379, 2.04901523, 10.14333127, -0.22475541, -6.83783e-03, -5.481717e-02, 1.22874e-03, 8.5282e-04,
              -1.99e-06]
        hi = C1[0] + (C1[1] * tempf) + (C1[2] * hum) + (C1[3] * tempf * hum) + (C1[4] * tempf ** 2) + (
                    C1[5] * hum ** 2) + (C1[6] * tempf ** 2 * hum) + (C1[7] * tempf * hum ** 2) + (
                         C1[8] * tempf ** 2 * hum ** 2)

        if tempf >= 80 and tempf <= 87 and hum > 85:
            adjustment = ((hum - 85) / 10) * ((87 - tempf) / 5)
            print("Made Adjustment")
            hi += adjustment

    return hi


# true means turn on fans
def decide_outcome(hi_interior, hi_exterior, precip, precip_1hr):
    return (hi_interior > hi_exterior and precip < 0.0001 and precip_1hr < 0.0001)


def set_fan_state(state):
    print("Set to " + str(state))


if __name__ == "__main__":
    main()
