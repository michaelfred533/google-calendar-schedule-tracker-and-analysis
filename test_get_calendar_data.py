import unittest
import schedule
import pandas as pd
import pandas.testing as pd_testing

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

class test_get_calendar_data(unittest.TestCase):


    def test_get_events(self):
        """
        Tests the basic function of google calendar API call for gathering calendar event data
        """


        # input:
        start_date = "2023-10-02"
        end_date = "2023-10-04"

        # output:
        service = schedule.access_calendar(SCOPES)
        result = schedule.get_events(service, start_date, end_date)

        # expected:
        expected = [
            {
                "status": "confirmed",
                "summary": "Test Case",
                "creator": {"email": "michaelfred@live.com", "self": True},
                "organizer": {"email": "michaelfred@live.com", "self": True},
                "start": {
                    "dateTime": "2023-10-02T13:00:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
                "end": {
                    "dateTime": "2023-10-02T14:00:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
            },
            {
                "status": "confirmed",
                "summary": "Test cas",
                "creator": {"email": "michaelfred@live.com", "self": True},
                "organizer": {"email": "michaelfred@live.com", "self": True},
                "start": {
                    "dateTime": "2023-10-03T14:00:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
                "end": {
                    "dateTime": "2023-10-03T14:30:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
            },
        ]

        # tests:
        self.assertEqual(len(result), 2)

        # event 1
        self.assertEqual(result[0]["status"], expected[0]["status"])
        self.assertEqual(result[0]["summary"], expected[0]["summary"])
        self.assertEqual(result[0]["creator"], expected[0]["creator"])
        self.assertEqual(result[0]["organizer"], expected[0]["organizer"])
        self.assertEqual(result[0]["start"], expected[0]["start"])
        self.assertEqual(result[0]["end"], expected[0]["end"])

        # event 2
        self.assertEqual(result[1]["status"], expected[1]["status"])
        self.assertEqual(result[1]["summary"], expected[1]["summary"])
        self.assertEqual(result[1]["creator"], expected[1]["creator"])
        self.assertEqual(result[1]["organizer"], expected[1]["organizer"])
        self.assertEqual(result[1]["start"], expected[1]["start"])
        self.assertEqual(result[1]["end"], expected[1]["end"])

    def test_get_events_max(self):
        """
        Testing edge case if more than 250 events (default max) are in the calendar 
        in the date range provided
        """


        # input:
        start_date = "2021-10-01"
        end_date = "2023-10-01"

        # output:
        service = schedule.access_calendar(SCOPES)
        result = schedule.get_events(service, start_date, end_date)

        # expected:
        # print(len(result))

        # tests:
        self.assertTrue(len(result) > 250)

    def test_get_events_empty(self):
        """
        Test that a ValueError is raised when an empty list is returned for the date range provided
        """


        # input:
        start_date = "2023-10-01"
        end_date = "2023-10-02"

        # output:

        # expected:
       
        # tests:
        service = schedule.access_calendar(SCOPES)
        with self.assertRaises(Exception) as assert_error:
            schedule.get_events(service, start_date, end_date)
        self.assertEqual(assert_error.exception.args[0], "No events found")

    def test_extract_event_data(self):
        """
        Tests basic function of properly extracting relevant data from the list of events provided by 
        google calendar API
        """

        
        # input:
        input = [
            {
                "status": "confirmed",
                "summary": "Test Case",
                "creator": {"email": "michaelfred@live.com", "self": True},
                "organizer": {"email": "michaelfred@live.com", "self": True},
                "start": {
                    "dateTime": "2023-10-02T13:00:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
                "end": {
                    "dateTime": "2023-10-02T14:00:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
            },
            {
                "status": "confirmed",
                "summary": "Test cas",
                "creator": {"email": "michaelfred@live.com", "self": True},
                "organizer": {"email": "michaelfred@live.com", "self": True},
                "start": {
                    "dateTime": "2023-10-03T14:00:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
                "end": {
                    "dateTime": "2023-10-03T14:30:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
            },
        ]

        # output:
        result_all_days, result_total = schedule.extract_event_data(input)

        # expected:
        expected_all_days = {
            "2023-10-02": {"test case": 60.0},
            "2023-10-03": {"test case": 30.0},
        }
        expected_total = {"test case": 90.0}

        # tests:
        self.assertEqual(result_all_days, expected_all_days)
        self.assertEqual(result_total, expected_total)

    def test_combine_data(self):
        """
        Tests basic function that the 2 dictionaries are combined into 1 
        """
        
        
        # input:
        expected_all_days = {
            "2023-10-02": {"test case": 60.0},
            "2023-10-03": {"test case": 30.0},
        }
        expected_total = {"test case": 90.0}

        # output:
        result = schedule.combine_data(expected_all_days, expected_total)

        # expected:
        expected = {
            "Days": ["2023-10-02", "2023-10-03"],
            "(test case) - time spent for each day": [60.0, 30.0],
            " Total time spent on each event": [90.0],
            "event Names": ["test case"],
        }

        # tests:
        self.assertEqual(result, expected)

    def test_create_csv(self):
        """
        Tests basic function that a proper dataframe is created from the combined data dictionary
        """

        # input:
        input = {
                "Days": ["2023-10-02", "2023-10-03"],
                "(test case) - time spent for each day": [60.0, 30.0],
                " Total time spent on each event": [90.0],
                "event Names": ["test case"],
            }
        # output:
        result = schedule.create_csv(input)

        # expected:
        data = [["2023-10-02", "2023-10-03"], [60.0, 30.0], [90.0, None], ["test case", None]]
        columns = ["Days", "(test case) - time spent for each day", " Total time spent on each event", "event Names"]
        expected = pd.DataFrame(data, columns).transpose()

        # tests:
        pd_testing.assert_frame_equal(expected, result)

if __name__ == "__main__":
    unittest.main()