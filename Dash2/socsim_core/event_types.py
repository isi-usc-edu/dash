
# general Socsim dictionaries
domains = {"cyber": 0, "CVE": 1, "crypto": 2}


# Github events, attributes
github_events_list = ["CreateEvent", "DeleteEvent", "PullRequestEvent", "PullRequestReviewCommentEvent", "IssuesEvent",
               "IssueCommentEvent", "PushEvent", "CommitCommentEvent","WatchEvent", "ForkEvent", "GollumEvent",
               "PublicEvent", "ReleaseEvent", "MemberEvent"]
github_events = {"CreateEvent": 0, "DeleteEvent": 1, "PullRequestEvent": 2, "PullRequestReviewCommentEvent": 3,
                       "IssuesEvent": 4, "IssueCommentEvent": 5, "PushEvent": 6, "CommitCommentEvent": 7, "WatchEvent": 8,
                       "ForkEvent": 9, "GollumEvent": 10, "PublicEvent": 11, "ReleaseEvent": 12, "MemberEvent": 13}

create_event_subtypes_list = ["tag", "branch", "repository"]
create_event_subtypes = {"repository": 2, "branch": 1, "tag": 0}

issue_and_pullrequest_event_subtypes_list = ["opened", "closed", "reopened"]
issue_and_pullrequest_event_subtypes = {"opened": 0, "closed": 1, "reopened": 2}



# Twitter
twitter_events_list = ["retweet", "reply", "quote", "tweet"]
twitter_events = {"retweet": 0, "reply": 1, "quote": 2, "tweet": 3}

# Reddit
reddit_events_list = ["post", "comment"]
reddit_events = {"post": 0, "comment": 1}
