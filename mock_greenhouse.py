"""Mock Greenhouse ATS API — realistic interview feedback data for ShipMonk CZ Tech."""

from collections import defaultdict


def get_mock_greenhouse_data():
    """Returns realistic mock data as if from Greenhouse API.

    Generates 28 feedback entries across 6 interviewers and 11 candidates,
    simulating ShipMonk's PHP Developer hiring pipeline with multiple round types.
    """
    return [
        # =====================================================================
        # CANDIDATE 1: Martin Kolar — Aces take-home, bombs tech interview
        # =====================================================================
        {
            "id": 1001,
            "interviewer": "Jan Nedbal",
            "candidate": "Martin Kolar",
            "role": "PHP Developer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["technical_skills", "problem_solving", "coding_ability"],
            "sentiment": -0.6,
            "date": "2026-01-14",
            "feedback_text": (
                "Technical interview was disappointing given the strength of the take-home submission. "
                "Martin struggled significantly with live coding under pressure. When asked to implement "
                "a simple repository pattern with Doctrine ORM, he could not articulate the difference "
                "between EntityManager::persist() and EntityManager::flush(), which is fundamental. "
                "His understanding of database indexes was superficial — he mentioned 'they make queries faster' "
                "but couldn't explain B-tree structures, composite indexes, or when an index might hurt performance. "
                "I suspect the take-home was completed with heavy AI assistance. His inability to explain "
                "his own architectural decisions from the submitted code was concerning. Score: 2/5. "
                "Decision: no hire."
            ),
            "round_type": "Technical Interview",
        },
        {
            "id": 1002,
            "interviewer": "Matej Smisek",
            "candidate": "Martin Kolar",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 4,
            "themes": ["coding_ability", "technical_skills"],
            "sentiment": 0.7,
            "date": "2026-01-10",
            "feedback_text": (
                "Take-home code review was solid. Martin submitted a clean Symfony application with "
                "well-structured service layer, proper use of dependency injection, and reasonable test coverage. "
                "The code follows PSR-12 standards and the README was thorough. He used Doctrine migrations "
                "correctly and his entity relationships were well thought out. The API design was RESTful "
                "with proper HTTP status codes and validation. A few minor issues: some services could "
                "benefit from interface extraction, and error handling was inconsistent in places. "
                "Overall a strong submission that demonstrates competence. Score: 4/5. Recommend hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1003,
            "interviewer": "Jakub Talacko",
            "candidate": "Martin Kolar",
            "role": "PHP Developer",
            "decision": "maybe",
            "score": 3,
            "themes": ["communication", "culture_fit"],
            "sentiment": 0.1,
            "date": "2026-01-16",
            "feedback_text": (
                "Culture fit round was mixed. Martin comes across as introverted and took a while to open up. "
                "He showed genuine interest in ShipMonk's mission and asked thoughtful questions about our "
                "warehouse automation challenges. However, I'm slightly concerned about how he'd fit into "
                "our collaborative environment — he mentioned preferring to work independently and seemed "
                "uncomfortable when I described our pair programming sessions. He was honest about his "
                "weaknesses, which I appreciate. On the fence overall. He might thrive in the right sub-team."
            ),
            "round_type": "Culture Fit",
        },

        # =====================================================================
        # CANDIDATE 2: Elena Svobodova — Strong across the board
        # =====================================================================
        {
            "id": 1004,
            "interviewer": "Jan Nedbal",
            "candidate": "Elena Svobodova",
            "role": "PHP Developer",
            "decision": "strong_hire",
            "score": 5,
            "themes": ["technical_skills", "system_design", "problem_solving"],
            "sentiment": 0.9,
            "date": "2026-02-05",
            "feedback_text": (
                "Outstanding technical interview. Elena demonstrated deep knowledge across the entire PHP "
                "ecosystem. Her explanation of PHP 8.3 fibers and how they compare to traditional async "
                "patterns was excellent. She whiteboarded a clean microservices architecture for our "
                "order processing pipeline, correctly identifying where to use message queues vs synchronous "
                "calls. Her database knowledge is exceptional — she explained covering indexes, query plan "
                "analysis with EXPLAIN, and even discussed InnoDB buffer pool tuning. When I pushed her on "
                "Doctrine's Unit of Work pattern and identity map, she explained it with precision. "
                "She also brought up DDD concepts like bounded contexts and aggregate roots organically. "
                "This is exactly the caliber of engineer we need. Score: 5/5. Strong hire."
            ),
            "round_type": "Technical Interview",
        },
        {
            "id": 1005,
            "interviewer": "Ondrej Netik",
            "candidate": "Elena Svobodova",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 4,
            "themes": ["coding_ability", "technical_skills"],
            "sentiment": 0.65,
            "date": "2026-02-03",
            "feedback_text": (
                "Elena's take-home submission was impressive. She built a well-architected Symfony 6 application "
                "with hexagonal architecture. The domain layer was properly separated from infrastructure "
                "concerns. Her use of value objects and custom Doctrine types showed maturity. Test coverage "
                "was above 80% with a good mix of unit and integration tests. She even included a Makefile "
                "and Docker setup for easy local development. One area for improvement: some of her service "
                "classes were doing too much — could benefit from further decomposition. But this is a minor "
                "point. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1006,
            "interviewer": "Jakub Talacko",
            "candidate": "Elena Svobodova",
            "role": "PHP Developer",
            "decision": "strong_hire",
            "score": 5,
            "themes": ["communication", "culture_fit", "leadership"],
            "sentiment": 0.85,
            "date": "2026-02-07",
            "feedback_text": (
                "Exceptional culture fit interview. Elena is articulate, collaborative, and clearly passionate "
                "about clean engineering. She asked excellent questions about our team dynamics and development "
                "process. She has experience mentoring junior developers and expressed enthusiasm about our "
                "knowledge-sharing culture. Her communication style is clear and she adapts well — she "
                "explained complex technical concepts in simple terms when I played the non-technical "
                "stakeholder role. She'd be a great addition to our team both technically and culturally. "
                "Score: 5/5. Strong hire."
            ),
            "round_type": "Culture Fit",
        },

        # =====================================================================
        # CANDIDATE 3: Petr Dvorak — Interviewers disagree completely
        # =====================================================================
        {
            "id": 1007,
            "interviewer": "Jan Nedbal",
            "candidate": "Petr Dvorak",
            "role": "PHP Developer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": -0.55,
            "date": "2026-01-22",
            "feedback_text": (
                "Petr's technical depth is insufficient for our bar. He could not explain the difference "
                "between hashing and encryption when asked directly — this is a basic security concept that "
                "any mid-level developer should know. His understanding of git was limited to basic "
                "commands; he didn't know what git rebase does or when you'd use it over merge. "
                "When asked about database normalization, he struggled past 2NF. His PHP knowledge is "
                "also shallow — he was unaware of named arguments, enums, or readonly properties introduced "
                "in PHP 8.x. I cannot recommend hiring someone with these fundamental gaps. Score: 2/5."
            ),
            "round_type": "Technical Quiz",
        },
        {
            "id": 1008,
            "interviewer": "Tomas Horvath",
            "candidate": "Petr Dvorak",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 4,
            "themes": ["problem_solving", "coding_ability", "communication"],
            "sentiment": 0.6,
            "date": "2026-01-20",
            "feedback_text": (
                "I was impressed by Petr's problem-solving approach during the take-home review. His code "
                "was pragmatic and well-organized. He used a clear MVC structure with proper separation of "
                "concerns. The solution handled edge cases well and included meaningful error messages. "
                "While the architecture wasn't as sophisticated as some submissions we see, the code was "
                "clean, readable, and would be easy to maintain. He clearly understands the fundamentals "
                "of building web applications. His communication during the walkthrough was clear and "
                "he was receptive to feedback. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1009,
            "interviewer": "Jakub Talacko",
            "candidate": "Petr Dvorak",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 4,
            "themes": ["culture_fit", "communication"],
            "sentiment": 0.7,
            "date": "2026-01-24",
            "feedback_text": (
                "Really enjoyed talking to Petr. He has a great attitude and would fit well into our team. "
                "He's curious, humble, and eager to learn. He talked about his experience transitioning "
                "from a small agency to wanting to work at a product company, and his reasons were "
                "thoughtful — he wants to own systems long-term rather than throw code over the wall. "
                "He asked great questions about our engineering culture, code review process, and how we "
                "handle technical debt. His collaborative mindset is exactly what we look for. "
                "Score: 4/5. Hire."
            ),
            "round_type": "Culture Fit",
        },

        # =====================================================================
        # CANDIDATE 4: Lucie Nemcova — Database knowledge weakness pattern
        # =====================================================================
        {
            "id": 1010,
            "interviewer": "Michal Dobias",
            "candidate": "Lucie Nemcova",
            "role": "PHP Developer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": 0.0,
            "date": "2025-12-12",
            "feedback_text": (
                "Lucie has decent PHP fundamentals but her database knowledge is a significant gap. "
                "She couldn't explain what a database index actually does at the storage level, and "
                "when asked about query optimization she only mentioned 'adding more indexes.' "
                "She was unaware of the N+1 problem in Doctrine ORM, which is critical for our "
                "high-throughput warehouse systems. Her PHP skills are acceptable — she understands "
                "OOP principles, interfaces, and basic design patterns. But for our workload where "
                "database performance is crucial, I'm on the fence. Score: 3/5."
            ),
            "round_type": "Technical Quiz",
        },
        {
            "id": 1011,
            "interviewer": "Jan Nedbal",
            "candidate": "Lucie Nemcova",
            "role": "PHP Developer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["technical_skills", "system_design"],
            "sentiment": -0.45,
            "date": "2025-12-14",
            "feedback_text": (
                "Technical interview confirmed the database weakness flagged in the quiz round. When I "
                "asked Lucie to design a schema for our inventory tracking system, she created a single "
                "monolithic table with no consideration for normalization or query patterns. She couldn't "
                "explain the difference between a clustered and non-clustered index. Her Doctrine knowledge "
                "is limited to basic CRUD operations — she hasn't worked with DQL, query builder optimization, "
                "or second-level cache. She also struggled with the system design portion, unable to "
                "articulate how she'd handle concurrent inventory updates. Not ready for our level. "
                "Score: 2/5. No hire."
            ),
            "round_type": "Technical Interview",
        },

        # =====================================================================
        # CANDIDATE 5: Tomas Novak — Solid but unspectacular
        # =====================================================================
        {
            "id": 1012,
            "interviewer": "Matej Smisek",
            "candidate": "Tomas Novak",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 4,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": 0.55,
            "date": "2026-02-18",
            "feedback_text": (
                "Tomas delivered a well-executed take-home. His Symfony application was cleanly structured "
                "with proper use of services, repositories, and DTOs. He implemented request validation "
                "using Symfony's validator component correctly. His API responses followed a consistent "
                "format with proper pagination. Test coverage was around 70% — decent but could be higher. "
                "Code quality was good overall, with clear naming conventions and appropriate use of "
                "type hints throughout. Nothing groundbreaking but solid, reliable work. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1013,
            "interviewer": "Ondrej Netik",
            "candidate": "Tomas Novak",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 3,
            "themes": ["technical_skills", "problem_solving"],
            "sentiment": 0.35,
            "date": "2026-02-20",
            "feedback_text": (
                "Technical quiz went reasonably well. Tomas correctly explained the difference between "
                "hashing and encryption, gave a solid answer on git rebase vs merge workflows, and "
                "showed adequate understanding of database indexes. His PHP knowledge is current — he's "
                "familiar with PHP 8.2 features. His Doctrine knowledge is practical but not deep. "
                "He had some gaps around more advanced topics like event listeners, custom Doctrine "
                "types, and cache regions. Overall, he meets the bar but doesn't exceed it. Score: 3/5. Hire."
            ),
            "round_type": "Technical Quiz",
        },

        # =====================================================================
        # CANDIDATE 6: Anna Prochazkova — Strong but fails culture fit
        # =====================================================================
        {
            "id": 1014,
            "interviewer": "Michal Dobias",
            "candidate": "Anna Prochazkova",
            "role": "PHP Developer",
            "decision": "strong_hire",
            "score": 5,
            "themes": ["technical_skills", "system_design", "coding_ability"],
            "sentiment": 0.8,
            "date": "2026-03-02",
            "feedback_text": (
                "Anna is technically brilliant. Her take-home was the best I've reviewed this quarter — "
                "clean DDD architecture with proper bounded contexts, event sourcing for the order flow, "
                "and comprehensive test suite including contract tests. She used PHP 8.3 features "
                "elegantly including typed class constants and the json_validate function. Her Doctrine "
                "setup was optimal with proper lazy loading strategies and custom repository methods. "
                "This is senior-level work. Score: 5/5. Strong hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1015,
            "interviewer": "Jakub Talacko",
            "candidate": "Anna Prochazkova",
            "role": "PHP Developer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["culture_fit", "communication"],
            "sentiment": -0.4,
            "date": "2026-03-04",
            "feedback_text": (
                "Despite Anna's obvious technical talent, I have serious concerns about culture fit. "
                "She was dismissive of our pair programming practice, calling it 'a waste of time for "
                "senior engineers.' When I described our collaborative code review process, she said "
                "she prefers to 'just get things done' without 'committee approval.' She was also "
                "critical of our tech stack choices without understanding the context behind them. "
                "Her communication style was blunt to the point of being abrasive. In a team environment "
                "like ours, attitude matters as much as technical skill. Score: 2/5. No hire."
            ),
            "round_type": "Culture Fit",
        },

        # =====================================================================
        # CANDIDATE 7: David Horak — Database weakness pattern
        # =====================================================================
        {
            "id": 1016,
            "interviewer": "Tomas Horvath",
            "candidate": "David Horak",
            "role": "PHP Developer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": 0.1,
            "date": "2025-12-20",
            "feedback_text": (
                "David's technical quiz showed a mixed picture. He's comfortable with PHP fundamentals "
                "and has decent Symfony experience. He correctly explained dependency injection and "
                "service containers. However, his database knowledge is weak — he confused foreign keys "
                "with indexes, and couldn't explain when you'd use a LEFT JOIN vs INNER JOIN in a "
                "practical scenario. His git knowledge was basic but functional. He understood "
                "hashing vs encryption at a high level but lacked depth. He has potential but would "
                "need significant mentoring on the database side. Score: 3/5. On the fence."
            ),
            "round_type": "Technical Quiz",
        },
        {
            "id": 1017,
            "interviewer": "Jan Nedbal",
            "candidate": "David Horak",
            "role": "PHP Developer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["technical_skills", "system_design"],
            "sentiment": -0.5,
            "date": "2025-12-22",
            "feedback_text": (
                "David's technical interview exposed critical gaps. His understanding of SQL query "
                "optimization is insufficient — he didn't know what EXPLAIN does and couldn't describe "
                "how a B-tree index works. When asked to design a warehouse inventory system, his "
                "schema had obvious normalization issues and no consideration for concurrent access. "
                "His Doctrine knowledge is limited to auto-generated CRUD. He hasn't worked with "
                "migrations beyond the basics and was unaware of Doctrine events. For our "
                "performance-critical systems, this level of database knowledge is inadequate. "
                "Score: 2/5. No hire."
            ),
            "round_type": "Technical Interview",
        },

        # =====================================================================
        # CANDIDATE 8: Katerina Mala — Junior but promising
        # =====================================================================
        {
            "id": 1018,
            "interviewer": "Matej Smisek",
            "candidate": "Katerina Mala",
            "role": "PHP Developer",
            "decision": "maybe",
            "score": 3,
            "themes": ["coding_ability", "technical_skills"],
            "sentiment": 0.2,
            "date": "2026-02-25",
            "feedback_text": (
                "Katerina's take-home showed potential but also revealed her junior level. The code "
                "was functional and well-organized, but lacked the architectural sophistication we "
                "look for. She used a basic MVC approach without service layer abstraction. Her tests "
                "were present but only covered happy paths. On the positive side, her code was clean, "
                "properly formatted, and she used type hints consistently. She clearly has good habits "
                "and a solid foundation to build on. The question is whether we're hiring for current "
                "ability or potential. Score: 3/5. Lean hire if we have bandwidth for mentoring."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1019,
            "interviewer": "Tomas Horvath",
            "candidate": "Katerina Mala",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 3,
            "themes": ["problem_solving", "communication", "culture_fit"],
            "sentiment": 0.4,
            "date": "2026-02-27",
            "feedback_text": (
                "Katerina's technical quiz revealed expected gaps for her experience level, but her "
                "approach to problems she didn't know was impressive. She was honest about what she "
                "didn't know, asked clarifying questions, and reasoned through problems logically. "
                "She correctly explained PHP arrays as ordered hash maps and knew the difference "
                "between == and ===. Her git knowledge was basic but she showed willingness to learn. "
                "Database knowledge is limited but she understood the concept of indexing even if "
                "she couldn't go deep. I think with 3-6 months of mentoring she'd be valuable. "
                "Score: 3/5. Hire — she has the right mindset."
            ),
            "round_type": "Technical Quiz",
        },

        # =====================================================================
        # CANDIDATE 9: Jiri Bartos — Consistently mediocre
        # =====================================================================
        {
            "id": 1020,
            "interviewer": "Michal Dobias",
            "candidate": "Jiri Bartos",
            "role": "PHP Developer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": -0.1,
            "date": "2026-01-08",
            "feedback_text": (
                "Jiri's take-home was average. The code works but lacks polish. He used procedural "
                "style in several places where OOP would be more appropriate. No tests were included, "
                "which is a red flag. His Symfony usage was basic — he didn't leverage the framework's "
                "strengths like form handling, event dispatchers, or the security component. Database "
                "queries were written as raw SQL instead of using Doctrine's query builder. The code "
                "would work in production but wouldn't be enjoyable to maintain. Score: 3/5. Borderline."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1021,
            "interviewer": "Ondrej Netik",
            "candidate": "Jiri Bartos",
            "role": "PHP Developer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "problem_solving"],
            "sentiment": 0.0,
            "date": "2026-01-10",
            "feedback_text": (
                "Technical quiz was underwhelming. Jiri gave surface-level answers to most questions. "
                "He knows the difference between hashing and encryption but couldn't name specific "
                "algorithms or when you'd use each. His git knowledge covers daily workflows but not "
                "more advanced operations like interactive rebase or bisect. Database index explanation "
                "was limited to 'they speed up queries.' He's been working with PHP for 5 years but "
                "his knowledge feels more like 1-2 years of depth. No clear strengths or weaknesses — "
                "just consistently below our bar across the board. Score: 3/5. Undecided."
            ),
            "round_type": "Technical Quiz",
        },

        # =====================================================================
        # CANDIDATE 10: Radek Vlcek — Good but database weakness
        # =====================================================================
        {
            "id": 1022,
            "interviewer": "Matej Smisek",
            "candidate": "Radek Vlcek",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 4,
            "themes": ["coding_ability", "technical_skills"],
            "sentiment": 0.5,
            "date": "2026-03-10",
            "feedback_text": (
                "Radek's take-home was well-crafted. Good use of Symfony's messenger component for "
                "async processing, clean controller layer with thin controllers delegating to services. "
                "His code was readable with meaningful variable names and helpful docblocks where needed. "
                "He implemented a proper command/query separation pattern. Test coverage included both "
                "unit tests with mocks and functional tests for API endpoints. One concern: his database "
                "migration had some inefficient column types and missing indexes on frequently queried "
                "columns. Overall a strong submission. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1023,
            "interviewer": "Jan Nedbal",
            "candidate": "Radek Vlcek",
            "role": "PHP Developer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "system_design"],
            "sentiment": -0.15,
            "date": "2026-03-12",
            "feedback_text": (
                "Radek showed strong application-level skills but his database and infrastructure "
                "knowledge needs work. He understood Doctrine's lazy loading and the N+1 problem, "
                "which is good. But when I pressed on index internals, query plan optimization, and "
                "database replication strategies, he reached his limits quickly. His system design "
                "answer for the order fulfillment pipeline was decent but lacked consideration for "
                "data consistency in distributed scenarios. He's a solid developer who could grow "
                "into the role but isn't there yet on the infrastructure side. Score: 3/5. Lean hire "
                "with mentoring plan."
            ),
            "round_type": "Technical Interview",
        },

        # =====================================================================
        # CANDIDATE 11: Marketa Hajkova — Great candidate, quick process
        # =====================================================================
        {
            "id": 1024,
            "interviewer": "Ondrej Netik",
            "candidate": "Marketa Hajkova",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 4,
            "themes": ["technical_skills", "problem_solving", "coding_ability"],
            "sentiment": 0.6,
            "date": "2026-03-05",
            "feedback_text": (
                "Marketa demonstrated solid technical skills in the quiz round. She confidently explained "
                "hashing vs encryption with real-world examples (bcrypt for passwords, AES for data at rest). "
                "Her git knowledge was thorough — she explained rebase vs merge with clear diagrams and "
                "when each is appropriate. Database indexes were explained well including composite indexes "
                "and covering indexes. She's currently using Doctrine with Symfony and demonstrated good "
                "understanding of entity lifecycle, DQL, and performance optimization. Her PHP knowledge "
                "is up to date with 8.2 features. Score: 4/5. Hire."
            ),
            "round_type": "Technical Quiz",
        },
        {
            "id": 1025,
            "interviewer": "Michal Dobias",
            "candidate": "Marketa Hajkova",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 4,
            "themes": ["coding_ability", "technical_skills"],
            "sentiment": 0.55,
            "date": "2026-03-07",
            "feedback_text": (
                "Strong take-home from Marketa. She built a clean REST API with Symfony 6.4, "
                "implementing CQRS-lite pattern with separate read and write models. Her test suite "
                "was comprehensive with factories for test data generation. She used PHP enums for "
                "status fields and readonly DTOs for data transfer — modern patterns applied correctly. "
                "The Docker setup was production-ready with multi-stage builds. Her database schema "
                "was well-designed with appropriate indexes and foreign key constraints. Minor note: "
                "some of the event handlers could be more focused. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": 1026,
            "interviewer": "Jakub Talacko",
            "candidate": "Marketa Hajkova",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 4,
            "themes": ["culture_fit", "communication", "leadership"],
            "sentiment": 0.65,
            "date": "2026-03-09",
            "feedback_text": (
                "Marketa was a pleasure to interview. She has experience working in agile teams and "
                "is comfortable with code reviews, sprint planning, and retrospectives. She asked "
                "insightful questions about our deployment pipeline and how we handle on-call rotations. "
                "She has experience mentoring junior developers at her current company and enjoys it. "
                "Her communication is clear and she listens actively. She expressed genuine excitement "
                "about ShipMonk's scale challenges. One thing I noticed is she's collaborative but also "
                "confident enough to push back on ideas — a great balance. Score: 4/5. Hire."
            ),
            "round_type": "Culture Fit",
        },

        # =====================================================================
        # Additional entries to flesh out interviewer patterns
        # =====================================================================

        # Jan Nedbal being consistently tough (another no_hire)
        {
            "id": 1027,
            "interviewer": "Jan Nedbal",
            "candidate": "Filip Cerny",
            "role": "PHP Developer",
            "decision": "no_hire",
            "score": 2,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": -0.65,
            "date": "2025-12-08",
            "feedback_text": (
                "Filip's technical interview was below expectations. His understanding of PHP internals "
                "is shallow — he couldn't explain how PHP handles memory management or what OPcache does. "
                "When asked about Doctrine's identity map and unit of work patterns, he had no idea what "
                "I was talking about. His database knowledge is inadequate: he couldn't explain transaction "
                "isolation levels or what ACID stands for. His code during the live exercise was poorly "
                "structured with no separation of concerns. Even basic concepts like interface segregation "
                "principle were foreign to him. He's been writing PHP for 3 years but his depth is "
                "concerning. Score: 2/5. Reject."
            ),
            "round_type": "Technical Interview",
        },

        # Tomas Horvath being more lenient
        {
            "id": 1028,
            "interviewer": "Tomas Horvath",
            "candidate": "Filip Cerny",
            "role": "PHP Developer",
            "decision": "maybe",
            "score": 3,
            "themes": ["coding_ability", "problem_solving"],
            "sentiment": 0.15,
            "date": "2025-12-06",
            "feedback_text": (
                "Filip's take-home was acceptable. The code worked and handled the main requirements. "
                "His approach was straightforward — not the most elegant solution but functional. "
                "He used some Symfony components correctly and his controller structure was reasonable. "
                "No tests, which I flagged, but the code itself was clean enough to be testable. "
                "His README explained the setup process clearly. I think he has potential but needs "
                "to develop more depth. With the right mentoring environment, he could grow. "
                "Score: 3/5. Maybe — depends on team capacity for mentoring."
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
            "company": "ShipMonk CZ Tech",
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
            "interviewer": "Matej Smisek",
            "candidate": "Vojtech Kral",
            "role": "PHP Developer",
            "decision": "hire",
            "score": 4,
            "themes": ["technical_skills", "coding_ability"],
            "sentiment": 0.5,
            "date": "2026-03-19",
            "feedback_text": (
                "Vojtech showed solid understanding of Symfony's service container and dependency injection. "
                "His take-home used a proper repository pattern with Doctrine. Code was clean with good "
                "test coverage. Score: 4/5. Hire."
            ),
            "round_type": "Take-home Review",
        },
        {
            "id": None,
            "interviewer": "Jan Nedbal",
            "candidate": "Vojtech Kral",
            "role": "PHP Developer",
            "decision": "maybe",
            "score": 3,
            "themes": ["technical_skills", "system_design"],
            "sentiment": 0.05,
            "date": "2026-03-19",
            "feedback_text": (
                "Vojtech's technical interview was mixed. Strong on application-level PHP patterns but "
                "struggled with database performance optimization questions. His understanding of Doctrine's "
                "unit of work was surface-level. Needs more depth on infrastructure topics. Score: 3/5."
            ),
            "round_type": "Technical Interview",
        },
    ]
    return get_mock_greenhouse_payload(sync_entries, id_offset=900000)
