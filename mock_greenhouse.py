"""Mock Greenhouse ATS API — realistic interview feedback data for Nexora Logistics Tech."""

from collections import defaultdict


def get_mock_greenhouse_data():
    """Returns realistic mock data as if from Greenhouse API.

    Generates 28 feedback entries across 6 interviewers and 11 candidates,
    simulating Nexora Logistics's Backend Engineer hiring pipeline with multiple round types.
    """
    return [
        # =====================================================================
        # CANDIDATE 1: Ryan Foster — Aces take-home, bombs tech interview
        # =====================================================================
        {
            "id": 1001,
            "interviewer": "Alex Mercer",
            "candidate": "Ryan Foster",
            "role": "Backend Engineer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["technical_skills", "problem_solving", "coding_ability"],
            "sentiment": -0.6,
            "date": "2026-01-14",
            "feedback_text": (
                "The technical interview was disappointing given the take-home submission. Ryan struggled "
                "significantly with live coding under pressure. I asked him to walk through a basic "
                "repository abstraction using an ORM — he couldn't explain the difference between "
                "staging an object and committing changes to the database, which is foundational. "
                "His knowledge of indexing was shallow: he said indexes make queries faster but "
                "couldn't discuss tree-based structures, composite keys, or situations where an index "
                "could hurt write performance. These are gaps you'd expect a mid-level engineer to "
                "cover confidently. He was unable to justify several architectural choices from the "
                "take-home when pressed — concerning given how polished the submission looked. "
                "Score: 2/5. No hire."
            ),
            "round_type": "Technical Interview",
        },
        {
            "id": 1002,
            "interviewer": "Sam Rivera",
            "candidate": "Ryan Foster",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 4,
            "themes": ["coding_ability", "technical_skills"],
            "sentiment": 0.7,
            "date": "2026-01-10",
            "feedback_text": (
                "Ryan's take-home was genuinely solid. He submitted a well-structured web application "
                "with a clean separation between the service layer and data access. Dependency injection "
                "was used correctly throughout and test coverage was reasonable. The API followed REST "
                "conventions with proper status codes and consistent response shapes. His README was "
                "thorough and the code followed style guidelines throughout. A couple of things could "
                "be improved: some service classes were doing too much and error handling was "
                "inconsistent in a few spots. But overall this was a confident, competent submission. "
                "Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1003,
            "interviewer": "Jordan Chen",
            "candidate": "Ryan Foster",
            "role": "Backend Engineer",
            "decision": "maybe",
            "score": 3,
            "themes": ["communication", "culture_fit"],
            "sentiment": 0.1,
            "date": "2026-01-16",
            "feedback_text": (
                "Culture fit was mixed. Ryan takes a while to warm up and is clearly more comfortable "
                "working independently. He asked good questions about the product direction and seemed "
                "genuinely interested in the logistics domain. My hesitation is around collaboration — "
                "he mentioned that he finds pair programming draining and prefers async code reviews. "
                "That's not disqualifying but it's worth discussing given how tightly our team works. "
                "He was candid about his weaknesses, which I respect. On the fence. Could work well "
                "in the right squad configuration. Score: 3/5."
            ),
            "round_type": "Culture Fit",
        },

        # =====================================================================
        # CANDIDATE 2: Priya Sharma — Strong across the board
        # =====================================================================
        {
            "id": 1004,
            "interviewer": "Alex Mercer",
            "candidate": "Priya Sharma",
            "role": "Backend Engineer",
            "decision": "strong_hire",
            "score": 5,
            "themes": ["technical_skills", "system_design", "problem_solving"],
            "sentiment": 0.9,
            "date": "2026-02-05",
            "feedback_text": (
                "Best technical interview I've conducted this quarter. Priya had deep, confident answers "
                "across every area. She explained async concurrency patterns clearly, drew a clean "
                "microservices architecture for our shipment tracking pipeline, and correctly identified "
                "which communication patterns to use synchronously versus via a message queue. Her "
                "database knowledge is exceptional — she walked through index internals, read EXPLAIN "
                "output fluently, and even brought up buffer pool configuration unprompted. When I "
                "pushed on ORM internals like the identity map and unit of work, she explained both "
                "precisely. She also introduced domain-driven design concepts like bounded contexts and "
                "aggregate roots naturally during the system design portion. This is exactly the level "
                "we need. Score: 5/5. Strong hire."
            ),
            "round_type": "Technical Interview",
        },
        {
            "id": 1005,
            "interviewer": "Taylor Kim",
            "candidate": "Priya Sharma",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 4,
            "themes": ["coding_ability", "technical_skills"],
            "sentiment": 0.65,
            "date": "2026-02-03",
            "feedback_text": (
                "Priya's take-home was impressive. She applied a hexagonal architecture with clear "
                "separation between domain, application, and infrastructure layers. Her domain model "
                "used value objects and custom types to enforce business rules. Test coverage was "
                "above 80% with both unit and integration tests. She included a Docker setup and a "
                "Makefile for local development — appreciated. One thing to flag: a few service "
                "classes had accumulated too many responsibilities and could be split further. That "
                "aside, the submission shows real architectural maturity. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1006,
            "interviewer": "Jordan Chen",
            "candidate": "Priya Sharma",
            "role": "Backend Engineer",
            "decision": "strong_hire",
            "score": 5,
            "themes": ["communication", "culture_fit", "leadership"],
            "sentiment": 0.85,
            "date": "2026-02-07",
            "feedback_text": (
                "Exceptional culture fit conversation. Priya is articulate, thoughtful, and clearly "
                "cares about the craft. She asked sharp questions about our team structure and "
                "engineering practices. She has mentored junior engineers in previous roles and spoke "
                "about it with real enthusiasm. Her communication adapts naturally — when I played a "
                "non-technical stakeholder, she shifted her explanation style immediately. She'd "
                "strengthen both the technical and cultural fabric of the team. Score: 5/5. Strong hire."
            ),
            "round_type": "Culture Fit",
        },

        # =====================================================================
        # CANDIDATE 3: Lucas Bennett — Interviewers disagree completely
        # =====================================================================
        {
            "id": 1007,
            "interviewer": "Alex Mercer",
            "candidate": "Lucas Bennett",
            "role": "Backend Engineer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": -0.55,
            "date": "2026-01-22",
            "feedback_text": (
                "Lucas doesn't meet our technical bar. He couldn't explain the difference between "
                "hashing and encryption — a basic security concept any mid-level engineer should know "
                "cold. His version control knowledge was limited to daily commands; he didn't understand "
                "what rebasing does or why you'd choose it over merging. On databases, he struggled "
                "past basic normalization and couldn't speak to normal forms with any confidence. His "
                "knowledge of modern language features was also shallow — unaware of named arguments, "
                "enums, and other widely adopted features. These aren't advanced topics. The gaps are "
                "too fundamental to overlook. Score: 2/5. No hire."
            ),
            "round_type": "Technical Quiz",
        },
        {
            "id": 1008,
            "interviewer": "Casey Walsh",
            "candidate": "Lucas Bennett",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 4,
            "themes": ["problem_solving", "coding_ability", "communication"],
            "sentiment": 0.6,
            "date": "2026-01-20",
            "feedback_text": (
                "I came away from the take-home review more positive than I expected. Lucas writes "
                "practical, readable code. His MVC structure was clean and the separation of concerns "
                "was clear. Edge cases were handled gracefully and his error messages were meaningful "
                "rather than generic. The architecture wasn't the most sophisticated we see, but it was "
                "coherent, maintainable, and delivered what was asked. He walked through his decisions "
                "well during our debrief and was receptive when I challenged a couple of his choices. "
                "Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1009,
            "interviewer": "Jordan Chen",
            "candidate": "Lucas Bennett",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 4,
            "themes": ["culture_fit", "communication"],
            "sentiment": 0.7,
            "date": "2026-01-24",
            "feedback_text": (
                "Genuinely enjoyed this conversation. Lucas has a great disposition — curious, low ego, "
                "and eager to grow. He's coming from a small agency background and is specifically "
                "looking for the kind of long-term product ownership that a company like ours offers. "
                "His reasoning for the move felt authentic rather than rehearsed. He asked thoughtful "
                "questions about our code review culture, how we handle legacy debt, and what growth "
                "looks like for engineers here. His collaborative instincts are strong. Score: 4/5. Hire."
            ),
            "round_type": "Culture Fit",
        },

        # =====================================================================
        # CANDIDATE 4: Sofia Andersen — Database knowledge weakness pattern
        # =====================================================================
        {
            "id": 1010,
            "interviewer": "Morgan Blake",
            "candidate": "Sofia Andersen",
            "role": "Backend Engineer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": 0.0,
            "date": "2025-12-12",
            "feedback_text": (
                "Sofia has reasonable application-level fundamentals but a clear gap in database "
                "knowledge. She couldn't explain what an index does at the storage level — just that "
                "it speeds things up. When asked about query optimization she defaulted to 'add more "
                "indexes' without considering write overhead or selectivity. She's also unfamiliar "
                "with the N+1 query problem, which is a real concern given how query-intensive our "
                "systems are. Her OOP knowledge is solid — she understands interfaces, abstract "
                "classes, and common design patterns. On the fence. Score: 3/5."
            ),
            "round_type": "Technical Quiz",
        },
        {
            "id": 1011,
            "interviewer": "Alex Mercer",
            "candidate": "Sofia Andersen",
            "role": "Backend Engineer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["technical_skills", "system_design"],
            "sentiment": -0.45,
            "date": "2025-12-14",
            "feedback_text": (
                "The technical interview confirmed what the quiz round flagged. When I asked Sofia to "
                "design a schema for an inventory tracking system, she produced a flat, denormalized "
                "structure with no consideration for query access patterns or concurrent writes. She "
                "couldn't articulate the difference between clustered and secondary indexes. Her ORM "
                "usage is limited to basic CRUD — she hasn't worked with query builder optimization, "
                "custom query languages, or second-level caching. The system design portion exposed "
                "further gaps: she had no strategy for handling concurrent inventory updates. "
                "Not at the level we need. Score: 2/5. No hire."
            ),
            "round_type": "Technical Interview",
        },

        # =====================================================================
        # CANDIDATE 5: Ethan Cole — Solid but unspectacular
        # =====================================================================
        {
            "id": 1012,
            "interviewer": "Sam Rivera",
            "candidate": "Ethan Cole",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 4,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": 0.55,
            "date": "2026-02-18",
            "feedback_text": (
                "Ethan delivered a well-executed take-home. His application was cleanly structured with "
                "thin controllers, a proper service layer, and repository abstractions. He used the "
                "framework's validation component correctly and his API responses were consistent with "
                "sensible pagination. Test coverage was around 70% — acceptable but I'd want to see "
                "higher. Code quality was good throughout: clear naming, appropriate use of type hints, "
                "no obvious code smells. Not groundbreaking, but solid and dependable. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1013,
            "interviewer": "Taylor Kim",
            "candidate": "Ethan Cole",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 3,
            "themes": ["technical_skills", "problem_solving"],
            "sentiment": 0.35,
            "date": "2026-02-20",
            "feedback_text": (
                "Technical quiz was reasonable. Ethan correctly explained hashing vs encryption, gave "
                "a clear answer on rebasing vs merging, and showed adequate database index knowledge. "
                "His understanding of modern language features is current. His ORM knowledge is "
                "practical but not deep — he's familiar with the basics but hasn't gone far into "
                "event listeners, custom types, or cache regions. He meets the bar without clearing it "
                "by much. Score: 3/5. Hire."
            ),
            "round_type": "Technical Quiz",
        },

        # =====================================================================
        # CANDIDATE 6: Claire Okafor — Strong but fails culture fit
        # =====================================================================
        {
            "id": 1014,
            "interviewer": "Morgan Blake",
            "candidate": "Claire Okafor",
            "role": "Backend Engineer",
            "decision": "strong_hire",
            "score": 5,
            "themes": ["technical_skills", "system_design", "coding_ability"],
            "sentiment": 0.8,
            "date": "2026-03-02",
            "feedback_text": (
                "Claire's take-home was the strongest submission I've reviewed this cycle. She applied "
                "a full DDD approach with proper bounded contexts, used event sourcing for the order "
                "flow, and wrote a comprehensive test suite including contract tests. She leveraged "
                "modern language features elegantly and her ORM configuration was optimized with "
                "explicit loading strategies and custom repository methods. This is senior-level work "
                "by any measure. Score: 5/5. Strong hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1015,
            "interviewer": "Jordan Chen",
            "candidate": "Claire Okafor",
            "role": "Backend Engineer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["culture_fit", "communication"],
            "sentiment": -0.4,
            "date": "2026-03-04",
            "feedback_text": (
                "I have serious concerns about team fit despite Claire's technical background. She was "
                "dismissive of pair programming, calling it inefficient for experienced engineers. "
                "When I described our collaborative code review process, she pushed back — said she'd "
                "rather ship than get stuck in 'design by committee.' Her attitude toward our stack was "
                "critical and lacking in curiosity about the constraints behind our choices. Her "
                "communication style was poor — blunt to the point of being off-putting rather than "
                "constructively direct. These are not gaps we can mentor around. Technical skill alone "
                "is insufficient in a team-first environment like ours. Score: 2/5. No hire."
            ),
            "round_type": "Culture Fit",
        },

        # =====================================================================
        # CANDIDATE 7: Marcus Webb — Database weakness pattern
        # =====================================================================
        {
            "id": 1016,
            "interviewer": "Casey Walsh",
            "candidate": "Marcus Webb",
            "role": "Backend Engineer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": 0.1,
            "date": "2025-12-20",
            "feedback_text": (
                "Mixed picture from the technical quiz. Marcus is comfortable with framework basics and "
                "has decent service container knowledge. He correctly explained dependency injection. "
                "However, his database knowledge is weak — he mixed up foreign keys and indexes at one "
                "point, and couldn't give a practical explanation of when to prefer a left join over "
                "an inner join. His version control knowledge is functional for day-to-day work. "
                "He has potential but would need real investment on the data layer side. "
                "Score: 3/5. On the fence."
            ),
            "round_type": "Technical Quiz",
        },
        {
            "id": 1017,
            "interviewer": "Alex Mercer",
            "candidate": "Marcus Webb",
            "role": "Backend Engineer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["technical_skills", "system_design"],
            "sentiment": -0.5,
            "date": "2025-12-22",
            "feedback_text": (
                "Technical interview exposed critical gaps in Marcus's database knowledge. He didn't "
                "know what EXPLAIN does or how a B-tree index is structured. When I asked him to design "
                "a warehouse inventory schema, it had obvious normalization issues and no handling for "
                "concurrent access patterns. His ORM usage appears limited to scaffolded CRUD — he "
                "hasn't worked with migrations beyond the basics and was unfamiliar with ORM event "
                "hooks. For systems where query performance is a first-class concern, this level of "
                "knowledge is insufficient. Score: 2/5. No hire."
            ),
            "round_type": "Technical Interview",
        },

        # =====================================================================
        # CANDIDATE 8: Zoe Patel — Junior but promising
        # =====================================================================
        {
            "id": 1018,
            "interviewer": "Sam Rivera",
            "candidate": "Zoe Patel",
            "role": "Backend Engineer",
            "decision": "maybe",
            "score": 3,
            "themes": ["coding_ability", "technical_skills"],
            "sentiment": 0.2,
            "date": "2026-02-25",
            "feedback_text": (
                "Zoe's take-home showed potential alongside clear signs of her experience level. The "
                "code is functional and organized, but the architecture is fairly flat — no real service "
                "layer abstraction and no interface usage. Tests only covered happy paths. On the "
                "positive side: the code is clean, formatting is consistent, and type hints are used "
                "throughout. She has good foundational habits. Whether we hire depends on whether "
                "we're staffing for current output or growth trajectory. Score: 3/5. Lean hire if "
                "there's bandwidth for mentoring."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1019,
            "interviewer": "Casey Walsh",
            "candidate": "Zoe Patel",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 3,
            "themes": ["problem_solving", "communication", "culture_fit"],
            "sentiment": 0.4,
            "date": "2026-02-27",
            "feedback_text": (
                "Zoe's quiz results were mixed for her experience level, but her approach to questions "
                "she didn't know stood out. She was upfront about knowledge gaps, asked clarifying "
                "questions before guessing, and reasoned through problems logically. She correctly "
                "explained the semantics of loose vs strict equality comparisons and understood the "
                "indexing concept conceptually even if she couldn't go deep. Her version control "
                "knowledge is basic but she was curious and engaged. With a few months of mentoring "
                "she'd be valuable. Score: 3/5. Hire — right mindset."
            ),
            "round_type": "Technical Quiz",
        },

        # =====================================================================
        # CANDIDATE 9: Owen Marsh — Consistently mediocre
        # =====================================================================
        {
            "id": 1020,
            "interviewer": "Morgan Blake",
            "candidate": "Owen Marsh",
            "role": "Backend Engineer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": -0.1,
            "date": "2026-01-08",
            "feedback_text": (
                "Owen's take-home was average. The application works but lacks polish. Several sections "
                "used a procedural style where OOP would have been more appropriate. No tests were "
                "included, which is a red flag for us. His framework usage was shallow — he didn't "
                "leverage built-in components for things like async dispatch or form validation. "
                "Database queries were written as raw strings rather than using the query builder. "
                "The code would run in production but maintaining it would be unpleasant. "
                "Score: 3/5. Borderline."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1021,
            "interviewer": "Taylor Kim",
            "candidate": "Owen Marsh",
            "role": "Backend Engineer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "problem_solving"],
            "sentiment": 0.0,
            "date": "2026-01-10",
            "feedback_text": (
                "Technical quiz was underwhelming. Owen gave surface-level answers across the board. "
                "He knows the conceptual difference between hashing and encryption but couldn't name "
                "common algorithms or reason through when you'd use each. His version control knowledge "
                "covers daily workflows but not more advanced operations. Database knowledge was "
                "reduced to 'indexes speed things up.' He's been in the industry several years but "
                "his depth feels much more shallow than his tenure would suggest. No strong areas, "
                "no strong weaknesses — just consistently below our bar. Score: 3/5. Undecided."
            ),
            "round_type": "Technical Quiz",
        },

        # =====================================================================
        # CANDIDATE 10: Dylan Torres — Good but database weakness
        # =====================================================================
        {
            "id": 1022,
            "interviewer": "Sam Rivera",
            "candidate": "Dylan Torres",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 4,
            "themes": ["coding_ability", "technical_skills"],
            "sentiment": 0.5,
            "date": "2026-03-10",
            "feedback_text": (
                "Dylan's take-home was well crafted. He used an async messaging pattern for background "
                "processing, kept controllers thin, and pushed logic into properly scoped services. "
                "Variable naming was clear and he added docblocks where they added value. He implemented "
                "command/query separation cleanly. Test coverage included unit tests with mocks and "
                "functional tests for the API. One concern: his database migration had inefficient "
                "column types and was missing indexes on columns that will clearly be queried heavily. "
                "Overall a strong submission. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1023,
            "interviewer": "Alex Mercer",
            "candidate": "Dylan Torres",
            "role": "Backend Engineer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "system_design"],
            "sentiment": -0.15,
            "date": "2026-03-12",
            "feedback_text": (
                "Dylan is capable at the application layer but struggled when we moved into database "
                "and infrastructure topics. He understood lazy loading and the N+1 problem, which is "
                "good. But when I pushed on index internals, query plan analysis, and replication "
                "strategies, the gaps became clear quickly. His system design answer for a fulfillment "
                "pipeline was adequate at the service level but didn't account for data consistency "
                "across distributed writes — a concerning miss for this role. He's a developer who "
                "could grow into it, but isn't there yet. Score: 3/5. Lean hire with a mentoring plan."
            ),
            "round_type": "Technical Interview",
        },

        # =====================================================================
        # CANDIDATE 11: Nina Castillo — Great candidate, quick process
        # =====================================================================
        {
            "id": 1024,
            "interviewer": "Taylor Kim",
            "candidate": "Nina Castillo",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 4,
            "themes": ["technical_skills", "problem_solving", "coding_ability"],
            "sentiment": 0.6,
            "date": "2026-03-05",
            "feedback_text": (
                "Nina was confident and precise throughout the quiz. She explained hashing vs encryption "
                "with concrete examples — password storage, data-at-rest encryption — without needing "
                "prompting. Her version control knowledge was thorough; she drew out rebase vs merge "
                "history clearly and articulated when each is the right call. Database indexes came "
                "with a solid explanation of composite indexes and covering indexes. She's working with "
                "an ORM daily and demonstrated fluent understanding of entity lifecycle and performance "
                "optimization. Her knowledge of recent language features is current. Score: 4/5. Hire."
            ),
            "round_type": "Technical Quiz",
        },
        {
            "id": 1025,
            "interviewer": "Morgan Blake",
            "candidate": "Nina Castillo",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 4,
            "themes": ["coding_ability", "technical_skills"],
            "sentiment": 0.55,
            "date": "2026-03-07",
            "feedback_text": (
                "Strong take-home from Nina. She implemented a CQRS-lite pattern with cleanly separated "
                "read and write models. Her test suite was comprehensive with factory helpers for "
                "generating test fixtures. She used enums for status fields and readonly value objects "
                "for data transfer — modern patterns applied correctly, not just cargo-culted. Docker "
                "setup was production-ready with multi-stage builds. Database schema was well thought "
                "through with appropriate indexes and proper foreign key constraints. Minor note: some "
                "event handlers were doing too much. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1026,
            "interviewer": "Jordan Chen",
            "candidate": "Nina Castillo",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 4,
            "themes": ["culture_fit", "communication", "leadership"],
            "sentiment": 0.65,
            "date": "2026-03-09",
            "feedback_text": (
                "Nina was a pleasure to talk with. She has strong agile experience and is comfortable "
                "with code reviews, sprint rituals, and retrospectives. She asked sharp questions about "
                "our deployment pipeline and on-call setup. She's mentored junior engineers at her "
                "current company and clearly enjoys it. Her communication is clear and she listens "
                "well. She expressed genuine interest in the scale challenges we're solving. One thing "
                "I noticed: she's collaborative but also confident enough to advocate for her positions "
                "when challenged — a healthy balance. Score: 4/5. Hire."
            ),
            "round_type": "Culture Fit",
        },

        # =====================================================================
        # Additional entries to flesh out interviewer patterns
        # =====================================================================

        # Alex Mercer being consistently tough (another no_hire)
        {
            "id": 1027,
            "interviewer": "Alex Mercer",
            "candidate": "Jake Harmon",
            "role": "Backend Engineer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": -0.65,
            "date": "2025-12-08",
            "feedback_text": (
                "Jake's technical interview was below the bar. He couldn't explain how the runtime "
                "manages memory or what bytecode caching does — these are things an engineer with "
                "several years of experience should have encountered. He had no familiarity with ORM "
                "internals like the identity map or unit of work pattern. Database knowledge was "
                "inadequate: he didn't know what transaction isolation levels are or what ACID "
                "guarantees mean in practice. His live coding produced loosely structured code with "
                "no separation of concerns. Even foundational design principles like interface "
                "segregation were unfamiliar to him. The experience on his CV doesn't match the "
                "depth in this interview. Score: 2/5. Reject."
            ),
            "round_type": "Technical Interview",
        },

        # Casey Walsh being more lenient
        {
            "id": 1028,
            "interviewer": "Casey Walsh",
            "candidate": "Jake Harmon",
            "role": "Backend Engineer",
            "decision": "maybe",
            "score": 3,
            "themes": ["coding_ability", "problem_solving"],
            "sentiment": 0.15,
            "date": "2025-12-06",
            "feedback_text": (
                "Jake's take-home was passable. The code delivered on the requirements and the "
                "overall structure was easy to follow. He used the framework's routing and some "
                "built-in components correctly. The approach was straightforward and coherent if "
                "unremarkable. No tests included, which I flagged — though the code was structured "
                "in a way that would make it testable. His README covered setup clearly. I think he "
                "has potential and might respond well to a solid mentoring environment. "
                "Score: 3/5. Maybe — depends on team capacity."
            ),
            "round_type": "Take-home Review",
        },
    ]


def _recommendation_from_decision(decision):
    mapping = {
        "strong_hire": "strong_yes",
        "hire": "yes",
        "maybe": "no_decision",
        "no_hire": "no",
        "strong_no_hire": "definitely_not",
    }
    return mapping.get(decision, "no_decision")


def _scorecard_questions(entry):
    return [
        {"id": None, "question": "Key Take-Aways", "answer": entry.get("feedback_text", "")[:500]},
        {"id": None, "question": "Private Notes", "answer": entry.get("feedback_text", "")[:500]},
        {"id": None, "question": "Themes", "answer": ", ".join(entry.get("themes", []))},
    ]


def _scorecard_attributes(entry):
    recommendation = _recommendation_from_decision(entry.get("decision"))
    attrs = []
    for theme in entry.get("themes", []):
        attrs.append({
            "name": theme.replace("_", " ").title(),
            "rating": recommendation,
            "note": entry.get("feedback_text", "")[:180],
        })
    if not attrs:
        attrs.append({"name": "Overall", "rating": recommendation, "note": entry.get("feedback_text", "")[:180]})
    return attrs


def _round_to_interview_step(round_type):
    mapping = {
        "Take-home Review": "Take Home Review",
        "Technical Quiz": "Technical Quiz",
        "Technical Interview": "Technical Interview",
        "Culture Fit": "Culture Interview",
        "System Design": "System Design",
    }
    return mapping.get(round_type, round_type or "General Interview")


def get_mock_greenhouse_payload(entries=None, id_offset=0):
    """Return a Greenhouse-like Harvest payload using realistic scorecard shapes."""
    entries = entries or get_mock_greenhouse_data()
    candidates = []
    scorecards = []
    grouped = defaultdict(list)
    interviewer_ids = {}

    for idx, entry in enumerate(entries, start=1):
        grouped[entry["candidate"]].append(entry)
        interviewer_ids.setdefault(entry["interviewer"], 9000 + len(interviewer_ids) + 1)
        candidate_id = 7000 + id_offset + abs(hash(entry["candidate"])) % 100000
        application_id = 8000 + id_offset + abs(hash(f"{entry['candidate']}::{entry['role']}")) % 100000
        stage_name = _round_to_interview_step(entry.get("round_type"))

        scorecards.append({
            "id": 50000 + id_offset + idx,
            "candidate_id": candidate_id,
            "application_id": application_id,
            "interview": {
                "id": 60000 + id_offset + idx,
                "name": stage_name,
            },
            "interview_step": {
                "id": 61000 + id_offset + idx,
                "name": stage_name,
            },
            "interviewed_at": f"{entry['date']}T10:00:00Z",
            "submitted_at": f"{entry['date']}T12:00:00Z",
            "submitted_by": {
                "id": interviewer_ids[entry["interviewer"]],
                "name": entry["interviewer"],
                "employee_id": None,
            },
            "interviewer": {
                "id": interviewer_ids[entry["interviewer"]],
                "name": entry["interviewer"],
                "employee_id": None,
            },
            "overall_recommendation": _recommendation_from_decision(entry.get("decision")),
            "attributes": _scorecard_attributes(entry),
            "questions": _scorecard_questions(entry),
        })

    for idx, (candidate_name, candidate_entries) in enumerate(grouped.items(), start=1):
        base = candidate_entries[0]
        candidate_id = 7000 + id_offset + abs(hash(candidate_name)) % 100000
        application_id = 8000 + id_offset + abs(hash(f"{candidate_name}::{base['role']}")) % 100000
        first_name, _, last_name = candidate_name.partition(" ")
        candidates.append({
            "id": candidate_id,
            "first_name": first_name,
            "last_name": last_name or "",
            "company": "Nexora Logistics",
            "title": base["role"],
            "created_at": f"{base['date']}T09:00:00Z",
            "updated_at": f"{base['date']}T12:00:00Z",
            "last_activity": f"{base['date']}T12:00:00Z",
            "applications": [
                {
                    "id": application_id,
                    "candidate_id": candidate_id,
                    "prospect": False,
                    "applied_at": f"{base['date']}T09:00:00Z",
                    "rejected_at": None,
                    "last_activity_at": f"{base['date']}T12:00:00Z",
                    "status": "active",
                    "jobs": [
                        {
                            "id": 3000 + idx,
                            "name": base["role"],
                        }
                    ],
                    "job_post_id": 4000 + idx,
                    "current_stage": {
                        "id": 5000 + idx,
                        "name": _round_to_interview_step(base.get("round_type")),
                    },
                    "answers": [],
                    "attachments": [],
                }
            ],
        })

    return {"scorecards": scorecards, "candidates": candidates}


def get_mock_greenhouse_sync_payload():
    """Return a smaller incremental payload that resembles a later Harvest sync."""
    sync_entries = [
        {
            "id": None,
            "interviewer": "Sam Rivera",
            "candidate": "Leo Grant",
            "role": "Backend Engineer",
            "decision": "hire",
            "score": 4,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": 0.5,
            "date": "2026-03-19",
            "feedback_text": (
                "Leo demonstrated solid understanding of service containers and dependency injection. "
                "His take-home used a clean repository pattern with proper ORM integration. Code was "
                "readable with good test coverage. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": None,
            "interviewer": "Alex Mercer",
            "candidate": "Leo Grant",
            "role": "Backend Engineer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "system_design"],
            "sentiment": 0.05,
            "date": "2026-03-19",
            "feedback_text": (
                "Leo's technical interview was mixed. Strong on application-level patterns but "
                "struggled with database performance optimization. His understanding of ORM internals "
                "was surface-level. Needs more depth on infrastructure topics. Score: 3/5."
            ),
            "round_type": "Technical Interview",
        },
    ]
    return get_mock_greenhouse_payload(sync_entries, id_offset=900000)
