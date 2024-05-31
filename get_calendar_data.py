"""
"""

from __future__ import print_function # must be at beginning of file

# 3rd party imports
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# built in imports
import datetime
from difflib import SequenceMatcher
import pandas as pd
import os.path


# If modifying these scopes, delete the file token.json.
# SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def access_calendar():
    """
    Calls the Google Calendar API and generates/updates credentials.json if needed

    Outputs: google calendar object
    """

    # 1) Gather credentials / log in --------------------------

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        # Refresh creds if they are expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        # Have user login to get creds
        else:
            flow = (
                InstalledAppFlow.from_client_secrets_file(  # construct instance of flow
                    "credentials.json", SCOPES
                )
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build(
        "calendar", "v3", credentials=creds
    )  # Creates the resource for interacting with the calendar api
    
    return service


def get_events(service, start_date, end_date):
    """
    Calls the Google Calendar API and pulls all the events in the calendar from within the date-range specified.

    Inputs: start date and end date to pull events from
    Outputs: list of calendar event items
    """


   
    # 2) Define the time period to collect data from --------------------

    start_date = (
        datetime.datetime.strptime(str(start_date), "%Y-%m-%d").isoformat() + "Z"
    )
    end_date = (
        datetime.datetime.strptime(str(end_date), "%Y-%m-%d").isoformat() + "Z"
    )

    # 3) Gather events from the Google Calendar API -------------------------------

    # BUG fix: Default value for maxResults in service.events().list() is 250, I set it to 2500 instead.
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_date,
            timeMax=end_date,
            singleEvents=True,
            maxResults=2500,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
        print("Caution: No events found!")
    return events


def extract_event_data(events):
    """
    Extract data from each event. Records the time spent on each activity within and across days.

    Input:
        events - List of event items pulled from Google Calendar
    Outputs:
        events_for_all_days_dict - a dictionary that contains the duration of each event for each day
        total_event_times_dict - a dictionary that contains a running total of the time spent of each activity
    """

    # 1) Gather data on each event --------------------

    events_for_all_days_dict = {}
    total_event_times_dict = {}

    for i, event in enumerate(events):
        # Extract the date and time of the start and the end of the event
        event_start_date = datetime.datetime.strptime(
            event["start"]["dateTime"], "%Y-%m-%dT%H:%M:%S%z"
        )
        event_end_date = datetime.datetime.strptime(
            event["end"]["dateTime"], "%Y-%m-%dT%H:%M:%S%z"
        )

        # Account for user-error in entry of event names: Strip leading and trailing spaces, and convert to lowercase.
        event_name = event["summary"].strip().lower()

        # Account for spelling errors by matching very closely related strings (eg. "reponding" and "responding")
        for name in total_event_times_dict.keys():
            ratio = SequenceMatcher(None, event_name, name).ratio()
            if (ratio != 1) & (ratio > 0.9):
                event_name = name

        current_day = event_start_date.date()

        # Define starting variables for the first iteration though the for-loop
        if i == 0:
            previous_day = event_start_date.date()
            events_for_current_day_dict = {}

        # Every time the iteration reaches a new day, save values for the previous day and create new variables for next day
        if previous_day != current_day:
            events_for_all_days_dict[str(previous_day)] = events_for_current_day_dict
            events_for_current_day_dict = {}
            previous_day = current_day

        event_duration = (
            event_end_date - event_start_date
        ).total_seconds() / 60  # Event duration in minutes

        # Add events to events_for_current_day_dicts to keep track of time spent for each day
        if event_name in events_for_current_day_dict.keys():
            events_for_current_day_dict[event_name] += event_duration
        else:
            events_for_current_day_dict[event_name] = event_duration

        # Add events separately to total_event_times_dict to track total time spent on each event over the entire data collection period
        if event_name in total_event_times_dict.keys():
            total_event_times_dict[event_name] += event_duration
        else:
            total_event_times_dict[event_name] = event_duration

        # Save the events from the last day
        if i == len(events) - 1:
            events_for_all_days_dict[str(previous_day)] = events_for_current_day_dict

    return events_for_all_days_dict, total_event_times_dict
    # -------------------- Save event data in a csv file to be uploaded to Tableau --------------------


def combine_data(events_for_all_days_dict, total_event_times_dict):
    # TODO: convert data to long form
    # TODO: 2 different data files instead of combining in 1

    # 1) Create empty lists for each activity
    set_of_all_events = set()
    combined_dict = {"Days": []}
    for day in events_for_all_days_dict.keys():
        combined_dict["Days"].append(day)
        for event in events_for_all_days_dict[day]:
            set_of_all_events.add(event)
            if (
                "(" + event + ")" + " - time spent for each day"
                not in combined_dict.keys()
            ):
                combined_dict["(" + event + ")" + " - time spent for each day"] = []

    # 2) Record the time spent on each activity for each day, or record 0 if the activity was not perfermed
    for day in combined_dict["Days"]:
        for event in list(set_of_all_events):
            if event in events_for_all_days_dict[day]:
                combined_dict["(" + event + ")" + " - time spent for each day"].append(
                    events_for_all_days_dict[day][event]
                )
            else:
                combined_dict["(" + event + ")" + " - time spent for each day"].append(
                    0
                )

    # 3) Create data columns for the event names and the total time spent on each activity

    event_totals_dict = {}
    (
        event_totals_dict[" Total time spent on each event"],
        event_totals_dict["event Names"],
    ) = ([], [])

    for event in total_event_times_dict.keys():
        event_totals_dict[" Total time spent on each event"].append(
            total_event_times_dict[event]
        )
        event_totals_dict["event Names"].append(event)

    return combined_dict, event_totals_dict

def convert_to_long(combined_dict):
    df = pd.DataFrame.from_dict(combined_dict)
    #print(df)
    df_long = pd.melt(df, id_vars = 'Days', value_vars = df.columns[1:])
    #print(df_long)

    return df_long


def create_csv(combined_dict):
    """
    input: combined_dict dictionary containing all data to be saved in csv format for export to Tableau
    output: A saved csv file in the directory
    """
    #TODO: fix this part w/ following 2 lines
    # The following 2 lines avoid the 'not equal length' error by filling in the remaining elements with nulls since our data columns differ in length.
    df = pd.DataFrame.from_dict(combined_dict, orient="index")
    df = (
        df.transpose()
    )  # Transpose returns data to a normal format recognized by Tableau
    df.to_csv("schedule_data.csv")

    # return the df so it can be used in the test_schedule script
    return df


if __name__ == "__main__":
    print("getting events...")
    service = access_calendar()
    events = get_events(service, "2022-05-01", "2022-10-01")
    events_for_all_days_dict, total_event_times_dict = extract_event_data(events)
    combined_dict_wide, event_totals_dict = combine_data(events_for_all_days_dict, total_event_times_dict)

    df_long = convert_to_long(combined_dict_wide)
    df_long.to_csv("schedule_data_long.csv")

    create_csv(combined_dict_wide)



    print("...finished")


## NOTES ---------------

# Add KPIs, need Measure, Tager, Frequency, Source (this tool)
