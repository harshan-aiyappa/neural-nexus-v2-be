// ===================================================
// CREATE NODES - 20 nodes, 6 types
// Types: Person, Company, Project, Technology, Location, Event
// ===================================================

CREATE
  // PERSONS (6)
  (p1:Person {id: 'p1', name: 'Priya Venkataraman', age: 34, role: 'CTO'}),
  (p2:Person {id: 'p2', name: 'Arjun Krishnamurthy', age: 29, role: 'Engineer'}),
  (p3:Person {id: 'p3', name: 'Kavitha Sundaram', age: 41, role: 'CEO'}),
  (p4:Person {id: 'p4', name: 'Rohan Iyer', age: 37, role: 'Data Scientist'}),
  (p5:Person {id: 'p5', name: 'Ananya Pillai', age: 26, role: 'Designer'}),
  (p6:Person {id: 'p6', name: 'Vikram Nair', age: 45, role: 'Investor'}),

  // COMPANIES (3)
  (c1:Company {id: 'c1', name: 'TatvaTech Solutions', founded: 2018, sector: 'AI'}),
  (c2:Company {id: 'c2', name: 'Drishtikon Analytics', founded: 2015, sector: 'Analytics'}),
  (c3:Company {id: 'c3', name: 'AkashNest Infra', founded: 2020, sector: 'Infrastructure'}),

  // PROJECTS (3)
  (pr1:Project {id: 'pr1', name: 'Project Chakravyuh', status: 'active', budget: 500000}),
  (pr2:Project {id: 'pr2', name: 'Project Vayu', status: 'completed', budget: 120000}),
  (pr3:Project {id: 'pr3', name: 'Project Nakshatra', status: 'planning', budget: 750000}),

  // TECHNOLOGIES (4)
  (t1:Technology {id: 't1', name: 'GraphQL', type: 'API', version: '16.0'}),
  (t2:Technology {id: 't2', name: 'Neo4j', type: 'Database', version: '5.x'}),
  (t3:Technology {id: 't3', name: 'PyTorch', type: 'ML Framework', version: '2.1'}),
  (t4:Technology {id: 't4', name: 'Kubernetes', type: 'Orchestration', version: '1.28'}),

  // LOCATIONS (2)
  (l1:Location {id: 'l1', name: 'Bengaluru', country: 'India', timezone: 'IST'}),
  (l2:Location {id: 'l2', name: 'Hyderabad', country: 'India', timezone: 'IST'}),

  // EVENTS (2)
  (e1:Event {id: 'e1', name: 'BharatAI Summit 2024', type: 'Conference', date: '2024-09-15'}),
  (e2:Event {id: 'e2', name: 'Series B Closing', type: 'Funding Round', date: '2024-11-01'})

// ===================================================
// RELATIONSHIPS - bidirectional, multi-hop, cross-links
// ===================================================

// --- Person → Company (WORKS_AT / FOUNDED / INVESTED_IN) ---
CREATE
  (p1)-[:WORKS_AT {since: 2019, equity: true}]->(c1),
  (p2)-[:WORKS_AT {since: 2021, equity: false}]->(c1),
  (p3)-[:FOUNDED {year: 2018}]->(c1),
  (p3)-[:WORKS_AT {since: 2018, equity: true}]->(c1),
  (p4)-[:WORKS_AT {since: 2020, equity: false}]->(c2),
  (p5)-[:WORKS_AT {since: 2022, equity: false}]->(c3),
  (p6)-[:INVESTED_IN {amount: 2000000, round: 'Series A'}]->(c1),
  (p6)-[:INVESTED_IN {amount: 500000, round: 'Seed'}]->(c3),

  // --- Person ↔ Person (KNOWS / MENTORS — bidirectional cross-links) ---
  (p1)-[:KNOWS {since: 2017, strength: 'strong'}]->(p3),
  (p3)-[:KNOWS {since: 2017, strength: 'strong'}]->(p1),
  (p1)-[:MENTORS {started: 2021}]->(p2),
  (p1)-[:MENTORS {started: 2022}]->(p5),
  (p4)-[:KNOWS {since: 2019, strength: 'weak'}]->(p2),
  (p2)-[:KNOWS {since: 2019, strength: 'weak'}]->(p4),
  (p6)-[:KNOWS {since: 2015, strength: 'strong'}]->(p3),
  (p3)-[:KNOWS {since: 2015, strength: 'strong'}]->(p6),

  // --- Person → Project (LEADS / CONTRIBUTES_TO — shared links) ---
  (p1)-[:LEADS {since: '2023-01'}]->(pr1),
  (p3)-[:LEADS {since: '2024-06'}]->(pr3),
  (p2)-[:CONTRIBUTES_TO {role: 'backend', hours_pw: 30}]->(pr1),
  (p4)-[:CONTRIBUTES_TO {role: 'ml-modeling', hours_pw: 20}]->(pr1),
  (p4)-[:CONTRIBUTES_TO {role: 'data-pipeline', hours_pw: 15}]->(pr2),
  (p5)-[:CONTRIBUTES_TO {role: 'ux', hours_pw: 25}]->(pr3),
  (p2)-[:CONTRIBUTES_TO {role: 'devops', hours_pw: 10}]->(pr3),

  // --- Company → Project (SPONSORS / OWNS — cross-links) ---
  (c1)-[:OWNS {since: '2023-01'}]->(pr1),
  (c1)-[:OWNS {since: '2024-06'}]->(pr3),
  (c2)-[:SPONSORS {amount: 80000}]->(pr1),
  (c2)-[:OWNS {since: '2022-03'}]->(pr2),
  (c3)-[:SPONSORS {amount: 150000}]->(pr3),

  // --- Project → Technology (USES — shared tech across projects) ---
  (pr1)-[:USES {since: '2023-02', critical: true}]->(t2),
  (pr1)-[:USES {since: '2023-02', critical: true}]->(t3),
  (pr1)-[:USES {since: '2023-05', critical: false}]->(t4),
  (pr2)-[:USES {since: '2022-04', critical: true}]->(t3),
  (pr2)-[:USES {since: '2022-04', critical: false}]->(t1),
  (pr3)-[:USES {since: '2024-07', critical: true}]->(t2),
  (pr3)-[:USES {since: '2024-07', critical: true}]->(t4),
  (pr3)-[:USES {since: '2024-08', critical: false}]->(t1),

  // --- Person → Technology (SKILLED_IN — cross-links back to persons) ---
  (p1)-[:SKILLED_IN {level: 'expert', years: 5}]->(t2),
  (p2)-[:SKILLED_IN {level: 'intermediate', years: 2}]->(t4),
  (p4)-[:SKILLED_IN {level: 'expert', years: 4}]->(t3),
  (p4)-[:SKILLED_IN {level: 'intermediate', years: 3}]->(t2),
  (p2)-[:SKILLED_IN {level: 'beginner', years: 1}]->(t1),

  // --- Company → Location (HEADQUARTERED_IN / HAS_OFFICE) ---
  (c1)-[:HEADQUARTERED_IN]->(l1),
  (c2)-[:HEADQUARTERED_IN]->(l2),
  (c3)-[:HEADQUARTERED_IN]->(l1),
  (c1)-[:HAS_OFFICE {since: 2021, headcount: 12}]->(l2),

  // --- Person → Location (BASED_IN) ---
  (p1)-[:BASED_IN]->(l1),
  (p2)-[:BASED_IN]->(l2),
  (p3)-[:BASED_IN]->(l1),
  (p4)-[:BASED_IN]->(l2),
  (p5)-[:BASED_IN]->(l1),
  (p6)-[:BASED_IN]->(l1),

  // --- Event cross-links (ATTENDED / HOSTED_BY / ANNOUNCED_AT) ---
  (p1)-[:ATTENDED {role: 'speaker'}]->(e1),
  (p3)-[:ATTENDED {role: 'keynote'}]->(e1),
  (p6)-[:ATTENDED {role: 'panelist'}]->(e1),
  (p4)-[:ATTENDED {role: 'attendee'}]->(e1),
  (c1)-[:HOSTED_BY]->(e1),
  (pr3)-[:ANNOUNCED_AT]->(e1),
  (p3)-[:ATTENDED {role: 'signatory'}]->(e2),
  (p6)-[:ATTENDED {role: 'lead-investor'}]->(e2),
  (c1)-[:HOSTED_BY]->(e2),

  // --- Technology dependencies (DEPENDS_ON — multi-hop chains) ---
  (t1)-[:DEPENDS_ON {type: 'runtime'}]->(t4),
  (t3)-[:DEPENDS_ON {type: 'compute'}]->(t4),
  (t2)-[:DEPENDS_ON {type: 'infra'}]->(t4);
