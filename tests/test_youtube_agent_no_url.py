import unittest
import json
import sys
import os
from unittest.mock import patch, MagicMock

# Ensure we can import modules from root
sys.path.append(os.getcwd())

from lucy_web_agent import youtube_agent


class TestYoutubeAgentNoUrl(unittest.TestCase):
    def test_empty_query_raises_no_url(self):
        with self.assertRaises(youtube_agent.NoYouTubeURLFound) as ctx:
            youtube_agent.find_youtube_video_url("")
        self.assertEqual(ctx.exception.code, "ERROR_NO_URL")

    @patch("lucy_web_agent.youtube_agent.subprocess.run")
    @patch("shutil.which")
    def test_invalid_candidate_raises_bad_url(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/yt-dlp"
        data = {
            "entries": [
                {
                    "title": "Bad Host",
                    "uploader": "Nope",
                    "webpage_url": "https://example.com/watch?v=bad",
                }
            ]
        }
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(data)
        mock_run.return_value = mock_proc

        with self.assertRaises(youtube_agent.BadYouTubeURL) as ctx:
            youtube_agent.find_youtube_video_url("algo")
        self.assertEqual(ctx.exception.code, "ERROR_BAD_URL")

    @patch("lucy_web_agent.youtube_agent.subprocess.run")
    @patch("shutil.which")
    def test_no_entries_raises_no_url(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/yt-dlp"
        data = {"entries": []}
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(data)
        mock_run.return_value = mock_proc

        with self.assertRaises(youtube_agent.NoYouTubeURLFound) as ctx:
            youtube_agent.find_youtube_video_url("algo")
        self.assertEqual(ctx.exception.code, "ERROR_NO_URL")


if __name__ == "__main__":
    unittest.main()
