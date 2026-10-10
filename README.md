# Creative analytics pipeline

Turns the five sample videos into a small dataset that an analyst can query with SQL or a notebook, and that an engineer can rebuild with one command.

## What I did and why

I had five videos and no audience data, so I split the work in two.

First I measured the videos themselves. The brief says the creatives can be a source of data, and they are the only real data I had. For every second of every video I record whether there is a scene cut, how much motion there is, how bright the picture is and how loud the audio is. This is the one part of the dataset that says something true about the five creatives.

Then I simulated an audience: viewers with demographics, viewing sessions, attention and engagement scores for each second watched, and survey answers. This data is made up. Its job is to show how the model holds the kinds of data the company actually collects, and what an analysis would look like once real data is plugged in. I kept the simulation simple on purpose: an average response per creative, a decline through the video, and noise.

Both halves are written to Parquet files and loaded into a DuckDB database. I chose DuckDB because it needs no server and uses standard SQL, and Parquet because the same files would load into any warehouse. On top of the raw tables there are two SQL views, so an analyst can start asking questions without writing joins.

A set of data checks runs on every build and stops it if anything is wrong. I would rather the pipeline fail than have bad data reach a chart.

Finally there is a notebook with three example analyses, and a file of example queries.

```text
creatives/*.mp4 --> extract_creatives.py --+
                                           +--> Parquet files --> DuckDB --> SQL / notebook
          seed --> generate_audience.py ---+
```



## Real vs synthetic data


| Data                                                               | Source                             | Tables                                                                                |
| ------------------------------------------------------------------ | ---------------------------------- | ------------------------------------------------------------------------------------- |
| Video metadata (duration, resolution, frame rate, orientation)     | Measured from the MP4s             | `raw.creatives`                                                                       |
| Per-second timeline (scene cuts, motion, brightness, loudness)     | Measured from the frames and audio | `raw.creative_timeline`                                                               |
| Viewers, viewing sessions, per-second biometrics, survey responses | Simulated with a fixed seed        | `raw.viewers`, `raw.viewing_sessions`, `raw.biometric_events`, `raw.survey_responses` |


Anything built on the simulated tables is an example of what the model lets you do. It is not a finding about these creatives.

## Running it

You need two things: [uv](https://docs.astral.sh/uv/getting-started/installation/) and the five sample videos.

**1. Get the code**

```bash
git clone https://github.com/nikosmakaritis/creative-analytics-pipeline.git
cd creative-analytics-pipeline
```

**2. Add the videos**

The videos are not in the repo. Create a `creatives/` folder at the root and put the five files in it, keeping the original filenames:

```text
creatives/
  Assume that I can - CoorDown.mp4
  E.L.F Cosmetics Lip Oil - @caro_manning.mp4
  E.L.F Cosmetics Lip Oil - @peytonxblack.mp4
  The Problem with Attention.mp4
  You Are Not Alone - Norwich City.mp4
```

**3. Install and run**

```bash
uv sync
make all
```

`uv sync` installs the Python libraries into a local `.venv` folder. `make all` then does everything, in under a minute:


| Step | Command on its own | What it does                                                   |
| ---- | ------------------ | -------------------------------------------------------------- |
| 1    | `make extract`     | Decodes each video and measures it second by second            |
| 2    | `make generate`    | Simulates the audience                                         |
| 3    | `make build`       | Loads the Parquet files into DuckDB and creates the views      |
| 4    | `make validate`    | Runs nine data checks and fails if any of them finds a bad row |
| 5    | `make notebook`    | Re-runs the notebook so its charts match the data              |
| 6    | `make open`        | Opens the notebook in the browser                              |


When it finishes you have `creative_analytics.duckdb` in the repo folder and the notebook open in your browser. Press Ctrl+C in the terminal to stop the notebook. `make open` opens it again later.

The Parquet files in `data/warehouse/` and the database file are generated, so they are not committed.

## Running SQL

Everything is in one file, `creative_analytics.duckdb`. Pick whichever way suits you.

**From the command line**

```bash
make sql
```

This opens a SQL prompt on the database. Type a query, end it with `;` and press Enter. `.quit` exits.

```sql
SHOW ALL TABLES;
DESCRIBE analytics.session_facts;
SELECT creative_id, round(avg(avg_attention), 3) AS attention
FROM analytics.session_facts
GROUP BY creative_id
ORDER BY attention DESC;
```

To run a single query without opening the prompt:

```bash
uv run duckdb creative_analytics.duckdb -c "SELECT * FROM raw.creatives"
```

To run all the example queries in one go:

```bash
uv run duckdb creative_analytics.duckdb < sql/examples.sql
```

**In the notebook**

Add a cell and use the `q()` helper. It runs a SQL string and returns a pandas DataFrame, so you can chart the result.

```python
q("SELECT age_group, avg(avg_attention) FROM analytics.session_facts GROUP BY age_group")
```

**In your own Python script**

```python
import duckdb
con = duckdb.connect("creative_analytics.duckdb", read_only=True)
con.sql("SELECT * FROM analytics.session_facts LIMIT 5").df()
```

**In the browser**

```bash
uv run duckdb creative_analytics.duckdb -ui
```

This opens DuckDB's own query editor as a local web page. It downloads a small extension the first time.

**In a desktop SQL app**

Any SQL client with a DuckDB driver can open the same file. In DBeaver, for example, create a new DuckDB connection and select `creative_analytics.duckdb`.

`[sql/examples.sql](sql/examples.sql)` has five queries to start from: how each video is edited, headline numbers per creative, attention through the video, attention by age group, and what was on screen next to average attention for one video.

## Data model


| Table                   | One row per        | Contents                                                                       |
| ----------------------- | ------------------ | ------------------------------------------------------------------------------ |
| `raw.creatives`         | video              | Name, brand, category and file metadata                                        |
| `raw.creative_timeline` | video and second   | `is_scene_cut`, `motion_score`, `brightness`, `audio_loudness_db`, `is_silent` |
| `raw.viewers`           | viewer             | `age_group`, `gender`, `region`                                                |
| `raw.viewing_sessions`  | viewer and video   | Watch time and completion                                                      |
| `raw.biometric_events`  | session and second | `attention_score`, `engagement_score` (0 to 1)                                 |
| `raw.survey_responses`  | session            | `brand_recall`, `likability`, `purchase_intent`, `emotional_impact`            |


The two views are plain SQL files in `[sql/views/](sql/views/)`:

- `analytics.session_facts` has one row per session with the viewer, the creative, the biometric averages and the survey answers joined in. This is where I'd start most questions.
- `analytics.attention_by_progress` has attention in 10% steps through each video, plus the share of viewers still watching.

Two choices in the analysis are worth explaining. Videos are compared by progress (0 to 100%) and not by seconds, because they run from 33 to 147 seconds. And the attention chart always shows how many viewers are left, because biometrics stop when someone leaves, so the later averages only describe the people who stayed.

## Limitations

- Scene-cut detection is a simple rule: a frame counts as a cut when it differs a lot from the previous one and clearly more than the frames around it. I checked it by eye against one video. It catches changes of location and framing but misses some jump cuts between similar shots.
- `brand` and `creative_category` are labelled by hand.
- The synthetic numbers are illustrative. They are not calibrated to any real study, and all of them are set in `[config.py](src/creative_analytics/config.py)`.
- Speech and on-screen text are not captured.
- You need the videos to build the data.

## With real data, and at scale

Each synthetic table is produced in one place, so swapping in a real source means replacing one Parquet file: a panel export for `viewers`, playback logs for `viewing_sessions`, biometric output for `biometric_events`, a survey export for `survey_responses`.

The overall shape would stay the same in production. The parts I'd expect to need real design work:

- Ingestion that is safe to replay. Biometric events will arrive late and duplicated, so I'd land them append-only and deduplicate on session and timestamp.
- Volume. Real biometrics are sampled many times a second. I'd keep the raw samples in partitioned storage and give analysts a per-second aggregate.
- New signals over time. A long format (`session, timestamp, signal, value`) takes new biometric measures without schema changes.
- Privacy and consent. This is sensitive data: pseudonymous viewer IDs, consent recorded per session, limits on retention and access.
- Monitoring of freshness, volume and failed checks per source.
- A hosted database, so analysts connect to it and never run the build themselves.

## What I'd do next

1. Add a transcript and on-screen text to the timeline.
2. Add the psychological-test data the brief mentions, as another session-level table.
3. Hand-label the scene cuts for a couple of videos and measure the detector against them.
4. Replace one synthetic table with a real sample.

