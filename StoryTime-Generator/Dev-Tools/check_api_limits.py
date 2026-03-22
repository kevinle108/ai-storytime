#!/usr/bin/env python3
"""
GitHub Models API Rate Limit Checker
Quickly check your API quota, remaining requests, and rate limit status.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
API_BASE_URL = "https://models.github.ai/inference"


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def check_token():
    """Verify GITHUB_TOKEN is configured"""
    if not GITHUB_TOKEN:
        print(f"{Colors.RED}❌ ERROR: GITHUB_TOKEN not found in .env file{Colors.RESET}")
        print(f"\n{Colors.CYAN}To fix this:{Colors.RESET}")
        print("1. Create a .env file in the StoryTime-Generator directory")
        print("2. Add: GITHUB_TOKEN=your_github_token_here")
        print("3. Get your token from: https://github.com/settings/personal-access-tokens")
        return False
    return True


def get_rate_limit_info():
    """Fetch rate limit information from GitHub Models API"""
    try:
        # Try to make a request and capture rate limit headers
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Make a simple request to get rate limit headers
        # This is a lightweight request that shows rate limit info in response headers
        response = requests.get(
            "https://api.github.com/rate_limit",
            headers={"Authorization": f"token {GITHUB_TOKEN}"}
        )
        
        if response.status_code == 200:
            return response.json(), response.headers
        else:
            return None, response.headers
            
    except Exception as e:
        print(f"{Colors.RED}Error fetching rate limit info: {str(e)}{Colors.RESET}")
        return None, None


def get_github_models_status():
    """Check GitHub Models API availability and basic quota"""
    try:
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Make a minimal request to GitHub Models to check availability
        payload = {
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 1,
            "temperature": 0.7
        }
        
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        rate_limit_limit = response.headers.get("x-ratelimit-limit-requests")
        rate_limit_remaining = response.headers.get("x-ratelimit-remaining-requests")
        rate_limit_reset = response.headers.get("x-ratelimit-reset-requests")
        
        return {
            "available": response.status_code != 403,
            "status_code": response.status_code,
            "limit": rate_limit_limit,
            "remaining": rate_limit_remaining,
            "reset": rate_limit_reset,
            "headers": response.headers
        }
    except requests.exceptions.Timeout:
        return {"error": "API timeout - server not responding"}
    except Exception as e:
        return {"error": str(e)}


def display_header():
    """Display header with timestamp"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}GitHub Models API Rate Limit Status{Colors.RESET}")
    print(f"{Colors.CYAN}Checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def display_rate_limits(data):
    """Display rate limit information in a readable format"""
    if not data:
        print(f"{Colors.YELLOW}ℹ️  Rate limit information not available{Colors.RESET}")
        return
    
    if "error" in data:
        print(f"{Colors.YELLOW}⚠️  {data['error']}{Colors.RESET}")
        return
    
    # GitHub API rate limits (from REST API)
    core = data.get("rate_limit", {}).get("core", {})
    
    if core:
        limit = core.get("limit", "N/A")
        remaining = core.get("remaining", "N/A")
        reset = core.get("reset", 0)
        
        print(f"{Colors.BOLD}GitHub REST API Rate Limits:{Colors.RESET}")
        print(f"  • Limit:     {limit} requests/hour")
        print(f"  • Remaining: {remaining}")
        
        # Calculate percentage
        if isinstance(limit, int) and isinstance(remaining, int):
            percentage = (remaining / limit) * 100
            
            # Color code based on percentage
            if percentage >= 75:
                status_color = Colors.GREEN
                status = "✅ GOOD"
            elif percentage >= 50:
                status_color = Colors.BLUE
                status = "ℹ️ MODERATE"
            elif percentage >= 25:
                status_color = Colors.YELLOW
                status = "⚠️ LOW"
            else:
                status_color = Colors.RED
                status = "🚨 CRITICAL"
            
            print(f"  • Status:    {status_color}{status}{Colors.RESET} ({percentage:.1f}% remaining)")
            
            if percentage < 25:
                print(f"\n{Colors.RED}⚠️ WARNING: API requests running low! Consider waiting before making more requests.{Colors.RESET}")
            elif percentage < 50:
                print(f"\n{Colors.YELLOW}⚠️ NOTICE: API requests at moderate level. Monitor usage.{Colors.RESET}")


def display_models_status(data):
    """Display GitHub Models API status"""
    print(f"\n{Colors.BOLD}GitHub Models API Status:{Colors.RESET}")
    
    if "error" in data:
        print(f"  {Colors.RED}❌ API Error: {data['error']}{Colors.RESET}")
        return
    
    if data.get("available"):
        print(f"  {Colors.GREEN}✅ API is available{Colors.RESET}")
    else:
        print(f"  {Colors.RED}❌ API returned: {data.get('status_code', 'Unknown error')}{Colors.RESET}")
    
    # Display rate limit headers if available
    limit = data.get("limit")
    remaining = data.get("remaining")
    reset = data.get("reset")
    
    if limit and remaining:
        print(f"\n{Colors.BOLD}Request Rate Limits (Models API):{Colors.RESET}")
        print(f"  • Limit:     {limit} requests")
        print(f"  • Remaining: {remaining} requests")
        
        # Calculate percentage
        try:
            limit_int = int(limit)
            remaining_int = int(remaining)
            percentage = (remaining_int / limit_int) * 100
            
            if percentage >= 75:
                status_color = Colors.GREEN
                status = "✅ GOOD"
            elif percentage >= 50:
                status_color = Colors.BLUE
                status = "ℹ️ MODERATE"
            elif percentage >= 25:
                status_color = Colors.YELLOW
                status = "⚠️ LOW"
            else:
                status_color = Colors.RED
                status = "🚨 CRITICAL"
            
            print(f"  • Status:    {status_color}{status}{Colors.RESET} ({percentage:.1f}% remaining)")
            
            if percentage < 10:
                print(f"\n{Colors.RED}🚨 CRITICAL: Very few requests remaining!{Colors.RESET}")
                print("   Consider waiting before making more API calls.")
            elif percentage < 25:
                print(f"\n{Colors.RED}⚠️ WARNING: Requests running low!{Colors.RESET}")
            elif percentage < 50:
                print(f"\n{Colors.YELLOW}⚠️ NOTICE: Requests at moderate level.{Colors.RESET}")
        except (ValueError, TypeError):
            pass
    
    if reset:
        print(f"  • Reset at:  {reset}")


def display_tips():
    """Display tips for managing API limits"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Tips for Managing API Quotas:{Colors.RESET}")
    print(f"  1. Check limits regularly before heavy workloads")
    print(f"  2. Use lower cost models (gpt-4o-mini) when possible")
    print(f"  3. Batch requests together when feasible")
    print(f"  4. Implement exponential backoff for retries")
    print(f"  5. Monitor costs in GitHub Settings")
    print(f"\n{Colors.BOLD}Learn More:{Colors.RESET}")
    print(f"  • GitHub Models Docs: https://models.github.ai/")
    print(f"  • GitHub Settings: https://github.com/settings")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def main():
    """Main function"""
    display_header()
    
    # Check if token is configured
    if not check_token():
        sys.exit(1)
    
    print(f"{Colors.CYAN}Fetching API information...{Colors.RESET}\n")
    
    # Get GitHub REST API rate limits
    rate_limit_data, headers = get_rate_limit_info()
    if rate_limit_data:
        display_rate_limits(rate_limit_data)
    
    # Get GitHub Models API status
    models_status = get_github_models_status()
    display_models_status(models_status)
    
    # Display helpful tips
    display_tips()


if __name__ == "__main__":
    main()
