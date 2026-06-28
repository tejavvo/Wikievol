-- =====================================================
-- WikiEvolution Database Schema (MariaDB/MySQL)
-- =====================================================

-- =====================================================
-- Table: WikiProject
-- =====================================================

CREATE TABLE WikiProject (
    project_id     INT AUTO_INCREMENT PRIMARY KEY,
    project_name   VARCHAR(255) NOT NULL,
    wiki_db        VARCHAR(255) NOT NULL
) ENGINE=InnoDB;
                  
-- =====================================================
-- Table: Article
-- =====================================================

CREATE TABLE Article (
    page_id             INT PRIMARY KEY,
    page_title          VARCHAR(255) NOT NULL,
    quality_class       VARCHAR(50),
    importance_class    VARCHAR(50),
    item_id             VARCHAR(50),
    wiki_db             VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

-- =====================================================
-- Table: Article_Project (Many-to-Many)
-- =====================================================

CREATE TABLE Article_Project (
    page_id     INT NOT NULL,
    project_id  INT NOT NULL,

    PRIMARY KEY (page_id, project_id),

    FOREIGN KEY (page_id)
        REFERENCES Article(page_id)
        ON DELETE CASCADE,

    FOREIGN KEY (project_id)
        REFERENCES WikiProject(project_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================
-- Table: Revision
-- =====================================================

CREATE TABLE Revision (
    revision_id         INT PRIMARY KEY,
    page_id             INT NOT NULL,

    revision_timestamp  VARCHAR(100) NOT NULL,
    month               VARCHAR(50) NOT NULL,

    page_length         INT,
    num_refs            INT,
    num_wikilinks       INT,
    num_categories      INT,
    num_media           INT,
    num_headings        INT,

    pred_qual           DOUBLE,

    FOREIGN KEY (page_id)
        REFERENCES Article(page_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================
-- Table: MonthlyAggregation
-- =====================================================

CREATE TABLE MonthlyAggregation (
    project_id          INT NOT NULL,
    month               VARCHAR(50) NOT NULL,

    num_articles        INT,

    mean_page_length    DOUBLE,
    sum_page_length     INT,

    mean_refs           DOUBLE,
    sum_refs            INT,

    mean_media          DOUBLE,
    sum_media           INT,

    mean_headings       DOUBLE,
    sum_headings        INT,

    mean_pred_qual      DOUBLE,

    PRIMARY KEY (project_id, month),

    FOREIGN KEY (project_id)
        REFERENCES WikiProject(project_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================
-- Useful Indexes
-- =====================================================

CREATE INDEX idx_article_title ON Article(page_title);
CREATE INDEX idx_revision_page ON Revision(page_id);
CREATE INDEX idx_revision_month ON Revision(month);
CREATE INDEX idx_revision_timestamp ON Revision(revision_timestamp);
CREATE INDEX idx_article_project_page ON Article_Project(page_id);
CREATE INDEX idx_article_project_project ON Article_Project(project_id);
CREATE INDEX idx_monthly_project ON MonthlyAggregation(project_id);
CREATE INDEX idx_monthly_month ON MonthlyAggregation(month);
