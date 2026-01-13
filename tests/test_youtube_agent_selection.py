import unittest
import json
import shutil
import sys
import os
from unittest.mock import patch, MagicMock

# Ensure we can import modules from root
sys.path.append(os.getcwd())

from lucy_web_agent import youtube_agent

class TestYoutubeAgentSelection(unittest.TestCase):
    
    def setUp(self):
        with open('tests/fixtures/yt_dlp_sample.json', 'r') as f:
            self.sample_data = json.load(f)
            self.sample_json = json.dumps(self.sample_data)

    @patch('lucy_web_agent.youtube_agent.subprocess.run')
    @patch('shutil.which')
    def test_yt_dlp_success_direct_url(self, mock_which, mock_run):
        """Should return the best candidate directly if yt-dlp works."""
        mock_which.return_value = '/usr/bin/yt-dlp'
        
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = self.sample_json
        mock_run.return_value = mock_proc
        
        url = youtube_agent.find_youtube_video_url("dolina entrevista")
        
        # Expect the first one because it matches "entrevista" (bonus keyword) and sorts well?
        # In the sample, "Entrevista a Alejandro Dolina"
        self.assertEqual(url, "https://www.youtube.com/watch?v=vid123")

    @patch('lucy_web_agent.youtube_agent.subprocess.run')
    @patch('shutil.which')
    def test_yt_dlp_no_threshold_logic(self, mock_which, mock_run):
        """Should pick the highest score even if low, instead of falling back to results?"""
        mock_which.return_value = '/usr/bin/yt-dlp'
        
        # Data with weak match
        data = {
            "entries": [
                {
                    "title": "Algo nada que ver",
                    "uploader": "X",
                    "webpage_url": "https://youtube.com/watch?v=bad"
                },
                {
                    "title": "Match debil palabra", 
                    "uploader": "Y",
                    "webpage_url": "https://youtube.com/watch?v=weak"
                }
            ]
        }
        
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(data)
        mock_run.return_value = mock_proc
        
        # Searching "palabra" should match "Match debil palabra"
        url = youtube_agent.find_youtube_video_url("palabra")
        
        # Previously it might return generic search_url if score was low.
        # Now it should return the best candidate.
        self.assertEqual(url, "https://youtube.com/watch?v=weak")

    @patch('shutil.which')
    @patch('lucy_agents.searxng_client.search')
    def test_searxng_fallback(self, mock_search, mock_which):
        """Should use SearXNG if yt-dlp is missing."""
        mock_which.return_value = None  # yt-dlp missing
        
        # SearXNG returns results
        mock_search.return_value = ([
            {"url": "https://other.com/video"},
            {"url": "https://www.youtube.com/watch?v=fallback123", "title": "Fallback Video"}
        ], [], "http://searx")
        
        url = youtube_agent.find_youtube_video_url("alguna cosa")
        
        self.assertEqual(url, "https://www.youtube.com/watch?v=fallback123")
        # Check that search was called with specialized query
        args, _ = mock_search.call_args
        self.assertIn("site:youtube.com watch alguna cosa", args[0])

if __name__ == '__main__':
    unittest.main()
