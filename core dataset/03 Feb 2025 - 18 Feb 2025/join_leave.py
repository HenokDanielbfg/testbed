import pandas as pd
import matplotlib.pyplot as plt

# Load datasets
handover_df = pd.read_csv("df_location.csv", parse_dates=["time"])
session_df = pd.read_csv("df_active.csv", parse_dates=["timestamp"])

# Figure 1: Handover Frequency Over Time
handover_df["hour"] = handover_df["time"].dt.hour
handover_timeline = handover_df.groupby("hour")["NrCellId"].count()
plt.figure(figsize=(10, 5))
plt.plot(handover_timeline.index, handover_timeline.values, marker='o')
plt.xlabel("Hour of the Day")
plt.ylabel("Number of Handovers")
plt.title("Handover Frequency Over Time")
plt.grid()
plt.savefig("handover_frequency.png")
plt.show()

# Figure 2: Most Frequent Handover Routes
handover_df.sort_values(by=["supi", "time"], inplace=True)
handover_df["PreviousCell"] = handover_df.groupby("supi")["NrCellId"].shift(1)
handover_routes = handover_df[handover_df["PreviousCell"].notna()].groupby(["PreviousCell", "NrCellId"]).size().reset_index(name="HandoverCount")
handover_routes = handover_routes.sort_values(by="HandoverCount", ascending=False).head(10)
plt.figure(figsize=(10, 5))
plt.barh(handover_routes.apply(lambda x: f"{int(x['PreviousCell'])} → {int(x['NrCellId'])}", axis=1), handover_routes["HandoverCount"], color='skyblue')
plt.xlabel("Number of Handovers")
plt.ylabel("Handover Routes")
plt.title("Most Frequent Handover Routes")
plt.gca().invert_yaxis()
plt.savefig("handover_routes.png")
plt.show()

# Figure 3: Average Time Before Handover Per Cell
handover_df["TimeDiff"] = handover_df.groupby("supi")["time"].diff().dt.total_seconds()
time_per_cell = handover_df.groupby("PreviousCell")["TimeDiff"].mean().reset_index()
time_per_cell = time_per_cell.dropna()
plt.figure(figsize=(10, 5))
plt.bar(time_per_cell["PreviousCell"].astype(int).astype(str), time_per_cell["TimeDiff"], color='coral')
plt.xlabel("Cell ID")
plt.ylabel("Average Time Before Handover (seconds)")
plt.title("Average Time Before Handover Per Cell")
plt.savefig("handover_time_per_cell.png")
plt.show()

# Figure 5: UE Session Duration Distribution
session_df["duration_seconds"] = pd.to_timedelta(session_df["duration"]).dt.total_seconds()
plt.figure(figsize=(10, 5))
plt.hist(session_df["duration_seconds"].dropna(), bins=20, color='purple', edgecolor='black')
plt.xlabel("Session Duration (seconds)")
plt.ylabel("Frequency")
plt.title("Distribution of UE Session Durations")
plt.savefig("ue_session_duration.png")
plt.show()

# Figure 6: Active UE Changes Over Time
plt.figure(figsize=(10, 5))
plt.plot(session_df["timestamp"], session_df["active_UEs"], marker='o', linestyle='-')
plt.xlabel("Time")
plt.ylabel("Number of Active UEs")
plt.title("Active UE Count Over Time")
plt.xticks(rotation=45)
plt.grid()
plt.savefig("active_ue_over_time.png")
plt.show()