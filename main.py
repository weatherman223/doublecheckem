import streamlit as st
import requests

def get_wcif(competition_id):
    """
    Fetches the World Cube Association Competition Information Format (WCIF) data for a given competition ID.

    Args:
        competition_id (str): The unique identifier of the WCA competition.

    Returns:
        dict: The WCIF data as a JSON-decoded Python dictionary.

    Raises:
        Exception: If the HTTP request fails or returns a non-200 status code, an exception is raised with details.
    """
    url = f"https://worldcubeassociation.org/api/v0/competitions/{competition_id}/wcif/public"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch WCIF for competition ID {competition_id}: {response.status_code} {response.text}")

def format_time(event_id, best):
    """
    Formats a competition result time or score based on the event type.

    Args:
        event_id (str): The event identifier (e.g., "333fm", "333mbf", etc.).
        best (int or None): The result value, typically in centiseconds for most events,
            or moves/count for special events.

    Returns:
        str: A formatted string representing the result:
            - For "333fm": returns "<best> moves".
            - For "333mbf": returns the string representation of best.
            - If best is None or 0: returns "-".
            - Otherwise, formats centiseconds as "M:SS.CC" or "S.CC".
    """
    if event_id == "333fm":
        return f"{best} moves"
    if event_id == "333mbf":
        return str(best)
    if best is None or best == 0:
        return "-"
    cs = int(best)
    minutes = cs // 6000
    seconds = (cs % 6000) // 100
    centis = cs % 100
    if minutes > 0:
        return f"{minutes}:{seconds:02d}.{centis:02d}"
    else:
        return f"{seconds}.{centis:02d}"
    
def find_top_competitors(wcif):
    """
    Analyzes a WCIF (WCA Competition Information Format) dictionary to identify top competitors in each event.

    For each event, iterates through registered persons and their personal bests to determine if they qualify as a top competitor based on world and national rankings:
    - For "single" results: selects competitors ranked top 100 in the world or top 30 nationally.
    - For "average" results: selects competitors ranked top 50 in the world or top 15 nationally.
    - Additionally, collects "borderline" competitors with world average rankings between 51 and 100.

    Args:
        wcif (dict): The WCIF data containing events and persons with their registration and personal bests.

    Returns:
        tuple:
            - results (dict): Mapping of event names to lists of top competitors, each as a dict with event/person/ranking info.
            - borderline (list): List of borderline competitors (world average ranking 51-100), each as a dict with relevant info.
    """

    results = {}
    borderline = []
    for event in wcif["events"]:
        event_id = event["id"]
        event_name = event.get("name", event_id)
        results[event_name] = []
        for person in wcif["persons"]:
            registration = person.get("registration")
            if not registration or registration.get("status") != "accepted":
                continue
            name = person.get('name', '[No Name]')
            wcaId = person.get('wcaId') or '[No WCA ID]'
            for pb in person.get("personalBests", []):
                if pb.get("eventId") != event_id:
                    continue
                pb_type = pb.get("type")
                wr = pb.get("worldRanking", float('inf'))
                nr = pb.get("nationalRanking", float('inf'))
                best = pb.get("best", 0)
                if best == 0 or wr == 0 or nr == 0:
                    continue
                rank_type = None
                ranking_value = None
                qualifier = None
                # Top list
                if pb_type == "single":
                    if wr <= 100 and nr <= 30:
                        rank_type = "World"
                        ranking_value = wr
                        qualifier = "WR"
                    elif wr <= 100:
                        rank_type = "World"
                        ranking_value = wr
                        qualifier = "WR"
                    elif nr <= 30:
                        rank_type = "National"
                        ranking_value = nr
                        qualifier = "NR"
                elif pb_type == "average":
                    if wr <= 50 and nr <= 15:
                        rank_type = "World"
                        ranking_value = wr
                        qualifier = "WR"
                    elif wr <= 50:
                        rank_type = "World"
                        ranking_value = wr
                        qualifier = "WR"
                    elif nr <= 15:
                        rank_type = "National"
                        ranking_value = nr
                        qualifier = "NR"
                    # Borderline: 51-100 world average
                    elif 51 <= wr <= 100:
                        borderline.append({
                            "event_id": event_id,
                            "event_name": event_name,
                            "name": name,
                            "wcaId": wcaId,
                            "ranking_value": int(wr),
                            "best": pb.get("best")
                        })
                if qualifier:
                    results[event_name].append({
                        "event_id": event_id,
                        "name": name,
                        "wcaId": wcaId,
                        "type": pb_type,
                        "ranking_value": int(ranking_value),
                        "rank_type": rank_type,
                        "qualifier": qualifier,
                        "best": pb.get("best")
                    })
    return results, borderline

st.title("Double Check Em!")
st.text("This app shows if you have a competitor signed up for the competition that meets the Groupfier Criteria for a double check.\n This is defined as:\n"
"1. Single: World Ranking <= 100 and National Ranking <= 30\n"
"2. Average: World Ranking <= 50 and National Ranking <= 15\n \n ")

comp_id = st.text_input("Enter Competition ID")

if st.button("Fetch WCIF"):
    if comp_id:
        try:
            wcif = get_wcif(comp_id)
            st.write("WCIF fetched successfully!")
            results, borderline = find_top_competitors(wcif)

            output = ["**Competitors that need double checks:**\n"]
            for event, competitors in results.items():
                if competitors:
                    output.append(f"**{event}:**")
                    for c in competitors:
                        type_display = "Single" if c["type"] == "single" else "Average"
                        time_display = format_time(c['event_id'], c['best'])
                        output.append(
                            f"- {c['name']} ({c['wcaId']}), {type_display}: "
                            f"{c['qualifier']} {c['ranking_value']}, Time: {time_display}"
                        )
                    output.append("")

            if borderline:
                output.append("**Borderline (51-100 World Ranking for Average):**")
                for c in borderline:
                    time_display = format_time(c['event_id'], c['best'])
                    output.append(
                        f"- {c['name']} ({c['wcaId']}), {c['event_name']}: "
                        f"WR {c['ranking_value']}, Time: {time_display}"
                    )

            st.markdown("\n".join(output))

        except Exception as e:
            st.error(f"Error fetching WCIF: {e}")
    else:
        st.error("Please enter a valid competition ID.")