# Testing Report
Run automated tests: `pytest -v`  (paste your output into the "Result" column below).

| ID | Feature | Test | Expected | Type | Result |
|----|---------|------|----------|------|--------|
| T1 | Analytics | pct_change(110,100) | 10 | auto | |
| T2 | Volatility | flat series | 0 | auto | |
| T3 | Volatility | random series + labels | >5, Low/High labels | auto | |
| T4 | Sentiment | positive / negative / neutral headline | 1 / -1 / 0 | auto | |
| T5 | AI model | forecast(300 pts,7) | 7 values inside 95% band | auto | |
| T6 | AI model | 20 points | ValueError | auto | |
| T7 | API | unsupported currency | HTTP 400 | auto | |
| T8 | API | malformed alert | HTTP 422 | auto | |
| T9 | API | create + delete alert; delete missing | 201 / 200 / 404 | auto | |
| M1 | Rates | Open dashboard | 9 rate cards with % change | manual | |
| M2 | Converter | 100 USD→INR | equals 100 × card rate | manual | |
| M3 | Chart | click 7D/30D/90D/1Y | chart + gain/loss redraw | manual | |
| M4 | Forecast | pick EUR→GBP | dashed line, metrics table shown | manual | |
| M5 | Heatmap | load | 10×10 grid, ranking line | manual | |
| M6 | Alerts | USD/INR above 1 | toast appears | manual | |
| M7 | Error handling | disconnect internet, restart | cached data still served | manual | |
| M8 | Responsive | resize to 375px / 768px | layout stacks, no sideways scroll | manual | |
