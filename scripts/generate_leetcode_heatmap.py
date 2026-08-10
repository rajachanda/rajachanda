#!/usr/bin/env python3
"""Generate a LeetCode heatmap SVG by querying LeetCode's GraphQL API.

Behavior:
- Attempt to fetch the user's `contributionCalendar` via LeetCode GraphQL.
- If network or parsing fails, fall back to a small placeholder heatmap.
- Embeds the user's solved count (if available) into the SVG as a badge-like text.

Usage: python scripts/generate_leetcode_heatmap.py <username> <out_path>
"""
import sys
import json
from datetime import datetime

USERNAME = sys.argv[1] if len(sys.argv) > 1 else 'chanda_raja_90'
out_path = sys.argv[2] if len(sys.argv) > 2 else 'assets/leetcode-heatmap.svg'

def fetch_leetcode_calendar(username: str):
  """Try to fetch contribution calendar and solved count from LeetCode GraphQL.
  Returns a dict with keys: months (list), solved_count (int) or raises on failure.
  """
  try:
    import requests
  except Exception:
    raise

  url = 'https://leetcode.com/graphql/'
  query = '''query userCalendar($username: String!) {
  matchedUser(username: $username) {
  contributionCalendar {
    totalActiveDays
    streak
    months {
    name
    year
    weeks {
      contributionDays {
      date
      contributionCount
      color
      }
    }
    }
  }
  submitStats {
    acSubmissionNum {
    difficulty
    count
    }
  }
  }
}'''

  payload = {"query": query, "variables": {"username": username}}
  headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'github-actions/leetcode-heatmap-generator'
  }

  # Add Referer/Origin to mimic browser origin — some endpoints require them
  headers.update({'Referer': f'https://leetcode.com/{username}/', 'Origin': 'https://leetcode.com', 'Accept': 'application/json'})
  resp = requests.post(url, json=payload, headers=headers, timeout=20)
  resp.raise_for_status()
  data = resp.json()
  mu = data.get('data', {}).get('matchedUser')
  if not mu:
    raise ValueError('No matchedUser in response')

  cal = mu.get('contributionCalendar') or {}
  months = cal.get('months') or []

  # Extract solved count (sum of acSubmissionNum entries where difficulty == 'All' or sum of counts)
  solved = None
  try:
    ac = mu.get('submitStats', {}).get('acSubmissionNum', [])
    # Find an entry with difficulty 'All' or sum counts
    solved_entry = next((e for e in ac if e.get('difficulty', '').lower() in ('all','overall')), None)
    if solved_entry:
      solved = int(solved_entry.get('count', 0))
    else:
      solved = sum(int(e.get('count', 0)) for e in ac)
  except Exception:
    solved = None

  return {'months': months, 'solved_count': solved}


def try_fetch_rating_from_profile(username: str):
  """Try to scrape a numeric 'rating' from the user's profile page HTML."""
  try:
    import requests, re
    url = f'https://leetcode.com/u/{username}/'
    headers = {'User-Agent': 'github-actions/leetcode-heatmap-generator', 'Referer': 'https://leetcode.com', 'Accept': 'text/html'}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
      return None
    html = r.text
    # Attempt to find a JSON snippet that contains "rating":NUMBER
    m = re.search(r'"rating"\s*:\s*(\d+)', html)
    if m:
      return int(m.group(1))
    # Fallback: find 'class="rating-number"' pattern
    m2 = re.search(r'class="rating-number">\s*(\d+)', html)
    if m2:
      return int(m2.group(1))
  except Exception:
    return None
  return None


def render_svg(months, username, solved_count):
  # Build cells from months->weeks->contributionDays
  cells = []
  max_weeks = 0
  for m in months:
    weeks = m.get('weeks', [])
    max_weeks = max(max_weeks, len(weeks))

  # We'll layout weeks horizontally, 7 rows (Sun-Sat). Iterate weeks across months
  # Collect weeks in order
  weeks_all = []
  for m in months:
    for w in m.get('weeks', []):
      weeks_all.append(w.get('contributionDays', []))

  # Determine width
  cell = 12
  gap = 6
  cols = max(1, len(weeks_all))
  width = 28 + cols * (cell + gap)
  height = 120

  for col_idx, week in enumerate(weeks_all):
    for day_idx, day in enumerate(week):
      x = 14 + col_idx * (cell + gap)
      y = 50 + day_idx * (cell + gap)
      count = day.get('contributionCount', 0)
      color = day.get('color') or '#0f172a'
      # fallback color map when color not provided
      if not color or color == '':
        if count == 0:
          color = '#0f172a'
        elif count < 2:
          color = '#0b3a2f'
        elif count < 5:
          color = '#11632f'
        elif count < 10:
          color = '#1f8a3a'
        else:
          color = '#34d399'
      cells.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{color}" />')

  solved_text = f'Solved: {solved_count}' if solved_count is not None else ''
  generated = datetime.utcnow().isoformat()

  svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
    f'  <rect width="{width}" height="{height}" fill="#0d1117" />',
    f'  <text x="14" y="26" fill="#00d9ff" font-family="Inter,Arial" font-size="16">LeetCode Heatmap — {username}</text>',
    f'  <text x="14" y="44" fill="#c9d1d9" font-family="Inter,Arial" font-size="11">Generated: {generated} UTC {solved_text}</text>',
    '  <g>'
  ]

  if cells:
    svg.append('    ' + '\n    '.join(cells))
  else:
    # placeholder small grid
    placeholder = []
    colors = ['#0f172a','#0b3a2f','#11632f','#1f8a3a','#34d399']
    for r in range(4):
      for c in range(6):
        x = 14 + c * (cell + gap)
        y = 60 + r * (cell + gap)
        color = colors[(r + c) % len(colors)]
        placeholder.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{color}" />')
    svg.append('    ' + '\n    '.join(placeholder))

  svg.append('  </g>')
  svg.append('</svg>')

  return '\n'.join(svg)


def main():
  try:
    data = fetch_leetcode_calendar(USERNAME)
    months = data.get('months', [])
    solved = data.get('solved_count')
    rating = try_fetch_rating_from_profile(USERNAME)
    svg = render_svg(months, USERNAME, solved)
    # Update README stats block if we have values
    try:
      if solved is not None or rating is not None:
        readme_path = 'README.md'
        with open(readme_path, 'r', encoding='utf-8') as rf:
          rd = rf.read()

        start = '<!-- LC_STATS_START -->'
        end = '<!-- LC_STATS_END -->'
        if start in rd and end in rd:
          before, rest = rd.split(start, 1)
          _, after = rest.split(end, 1)
          rating_text = str(rating) if rating is not None else 'dynamic (see card)'
          solved_text = str(solved) if solved is not None else 'dynamic (see card)'
          new_block = f"{start}\n```txt\nLeetCode Rating  : {rating_text}\nProblems Solved  : {solved_text}\nCodeChef         : add your CodeChef handle to show badge\n```\n{end}"
          new_rd = before + new_block + after
          with open(readme_path, 'w', encoding='utf-8') as wf:
            wf.write(new_rd)
    except Exception as e2:
      print('Warning: failed to update README with stats:', e2)
  except Exception as e:
    # fallback to previous placeholder behavior
    print('Warning: failed to fetch live data, using placeholder:', e)
    # create a small placeholder
    colors = ['#0f172a','#0b3a2f','#11632f','#1f8a3a','#34d399']
    cells = []
    for r in range(5):
      for c in range(6):
        x = c * 18
        y = r * 18
        color = colors[(r + c) % len(colors)]
        cells.append(f'<rect x="{x}" y="{y}" width="14" height="14" rx="2" fill="{color}" />')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="620" height="180">
  <rect width="620" height="180" fill="#0d1117" />
  <text x="14" y="26" fill="#00d9ff" font-family="Inter,Arial" font-size="16">LeetCode Heatmap — {USERNAME}</text>
  <text x="14" y="44" fill="#c9d1d9" font-family="Inter,Arial" font-size="11">Generated: {datetime.utcnow().isoformat()} UTC</text>
  <g transform="translate(14,60)">\n    {'\n    '.join(cells)}\n  </g>
</svg>'''

  with open(out_path, 'w', encoding='utf-8') as f:
    f.write(svg)

  print('Wrote', out_path)


if __name__ == '__main__':
  main()
