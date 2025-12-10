"""
Grade definitions for role-specific requirements.
Used for resume scoring against company grade standards.
"""

T2_GRADE = {
    "Grade": "T2",
    "Title": "Technical Specialist (Software Eng, System Eng, QA Eng etc.)",
    "Technical Skills": {
        "Platform knowledge": "Reliable expertise in a relevant platform — C\\C++, Java, .NET, embedded systems, blackbox\\whitebox testing, OS, networking, etc.",
        "Products knowledge": "Reliable expertise in the relevant software stacks — JEE, SpringSource, Solaris, VMWare ESX, Mercury QC, etc.",
        "Computer science": "Working knowledge of fundamental algorithms and implementation data structures — lists, hash tables, trees.",
        "Technical writing": "Good knowledge of written English language (technical). Ability to document own deliverables (code, tests, scripts, etc.).",
        "Tools knowledge": "Fully competent with the de-facto standard tools that are used within the company — project management tools, build systems, version control systems, virtualization technologies, monitoring etc.",
        "Quality assurance": "Fully understands testability concepts, writes unit tests for own code."
    },
    "Organizational skills": {
        "Delivery": "Reliably deliver on all commitments, requiring little supervision.",
        "Communication": "Frequent communication with all team members on development issues. Reliably communicate status and promptly escalate issues to the team leader.",
        "Culture": "Maintain a professional image, composure and attitude at all customer-facing activities. Understand all company announcements."
    },
    "Peopleware": {
        "Mentoring": "Provide recommendations of team members performance ratings. Provide informal mentoring and advise junior members on career management issues.",
        "Interviews": "Primary interviewer for T1 hires; participate in occasional T2 interviews."
    },
    "Thought leadership": {
        "Knowledge sharing": "Sharing information through blogs or tech talks.",
        "Community activities": "Communication with open-source or professional communities on occasional basis.",
        "Innovation": "Open to the use of innovative solutions; participates in team innovation-producing exercises."
    },
    "Project management": {
        "Project lifecycle": "Fully understand goals and approaches of the assigned project. Assist in requirements gathering.",
        "Processes": "Works in the process defined by the team lead."
    },
    "Experience": {
        "Industry experience": "1+ years of experience in the relevant industry."
    }
}

T3_GRADE = {
    "Grade": "T3",
    "Title": "Senior Technical Specialist (Sr. Software Eng, Sr. System Eng, Sr. QA Eng etc.)",
    "Technical Skills": {
        "Platform knowledge": "Reliable expertise for one relevant platform and familiarity with additional platforms; contribute to architectural analysis and decisions.",
        "Products knowledge": "Strong expertise in one technology/solution strategically important to the company, familiarity with at least one additional; recommend selections.",
        "Computer science": "Strong understanding of algorithms complexity, parallelization problems, multithreading, functional concepts; able to design own data structures from scratch.",
        "Technical writing": "Strong knowledge of written English language (technical). Able to write project documentation, design and implement architecture diagrams.",
        "Tools knowledge": "Fully competent with the de-facto standard tools that are used within the company. Working knowledge of diagram design tools and presentation software.",
        "Quality assurance": "Fully understands testability concepts. Responsible for quality metrics on one or several major components.",
    },
    "Organizational skills": {
        "Delivery": "Responsible for delivery on one or several major components; can be responsible for delivery of a minor project.",
        "Communication": "Strong command of English beyond purely technical issues; able to politely present and defend ideas in blogging, presentations etc. Has frequent contact across the functional organizations. Communicate directly with client or partner architects, engineers, and project managers.",
        "Culture": "When required to travel to client or pre-sales meetings, be capable of interacting with the local environment.",
    },
    "Peopleware": {
        "Mentoring": "Mentor at least one junior engineer on the project, emphasizing engineering and development methodology improvements.",
        "Interviews": "Primary interviewer for T2 hires; participate in occasional T3 interviews.",
    },
    "Thought leadership": {
        "Knowledge sharing": "Frequent blogger, or frequent tech talk speaker. Recognized by the peers as a credible source of information on the topic.",
        "Community activities": "Attend conferences or contribute into open-source projects.",
        "Innovation": "Acknowledged by peers as having delivering at least one innovative solution.",
    },
    "Project management": {
        "Project lifecycle": "Understand and document detailed requirements to the project. Recommend resources and timelines.",
        "Processes": "Works in the process defined by the team lead. Active supporter of the chosen process, recommends improvements.",
    },
    "Experience": {
        "Industry experience": "3+ years of experience in the relevant industry.",
    }
}

GRADES = {
    "T2": T2_GRADE,
    "T3": T3_GRADE,
}


def get_grade(grade: str):
    """
    Get grade definition by grade code.
    
    Args:
        grade: Grade code (e.g., "T2", "T3")
        
    Returns:
        Grade dictionary or None if not found
    """
    return GRADES.get(grade.upper())


def format_grade_requirements(grade_data: dict) -> str:
    """
    Format grade requirements into a readable string for the LLM prompt.
    
    Args:
        grade_data: Grade dictionary with requirements
        
    Returns:
        Formatted string of requirements
    """
    if not grade_data:
        return ""
    
    lines = [f"Grade: {grade_data.get('Grade', 'Unknown')} - {grade_data.get('Title', '')}"]
    lines.append("")
    
    for category, requirements in grade_data.items():
        if category in ["Grade", "Title"]:
            continue
        
        lines.append(f"{category}:")
        if isinstance(requirements, dict):
            for key, value in requirements.items():
                lines.append(f"  - {key}: {value}")
        else:
            lines.append(f"  {requirements}")
        lines.append("")
    
    return "\n".join(lines)


