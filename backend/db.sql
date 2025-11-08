-- Start of script ----------------------------------------------------------
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS comments CASCADE;
DROP TABLE IF EXISTS attachments CASCADE;
DROP TABLE IF EXISTS task_collaborators CASCADE;
DROP TABLE IF EXISTS project_collaborators CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS users CASCADE;

DROP TYPE IF EXISTS userrole_enum;
DROP TYPE IF EXISTS taskstatus_enum;
DROP TYPE IF EXISTS projectstatus_enum;
DROP TYPE IF EXISTS notificationtype_enum;
DROP TYPE IF EXISTS recurrencetype_enum;

-- ENUM types ----------------------------------------------------------------

CREATE TYPE userrole_enum AS ENUM (
    'STAFF',
    'MANAGER',
    'DIRECTOR',
    'HR'
);

CREATE TYPE taskstatus_enum AS ENUM (
    'Unassigned',
    'Ongoing',
    'Pending Review',
    'Completed'
);

CREATE TYPE projectstatus_enum AS ENUM (
    'Not Started',
    'In Progress',
    'Completed'
);

CREATE TYPE notificationtype_enum AS ENUM (
    'due_date_reminder',
    'new_comment',
    'task_updated',
    'project_updated',
    'task_assignment',
    'project_assignment'
);

CREATE TYPE recurrencetype_enum AS ENUM (
    'none',
    'daily',
    'weekly',
    'monthly',
    'custom'
);

-- USERS --------------------------------------------------------------------

CREATE TABLE users (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role          userrole_enum NOT NULL DEFAULT 'STAFF',
    name          VARCHAR(80) NOT NULL,
    email         VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(512) NOT NULL
);

-- PROJECTS -----------------------------------------------------------------

CREATE TABLE projects (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(160) NOT NULL,
    description TEXT,
    notes       TEXT,
    deadline    DATE,
    status      projectstatus_enum NOT NULL DEFAULT 'Not Started',
    owner_id    INTEGER NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT fk_projects_owner
        FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE RESTRICT
);

-- TASKS --------------------------------------------------------------------

CREATE TABLE tasks (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title              VARCHAR(50) NOT NULL,
    description        VARCHAR(200),
    duedate            DATE NOT NULL,
    status             taskstatus_enum NOT NULL DEFAULT 'Unassigned',
    created_at         TIMESTAMP WITH TIME ZONE DEFAULT now(),
    notes              VARCHAR(500),
    owner_id           INTEGER NOT NULL,
    project_id         INTEGER,
    priority           INTEGER NOT NULL DEFAULT 1,
    isRecurring        BOOLEAN NOT NULL DEFAULT FALSE,
    recurrence_type    recurrencetype_enum NOT NULL DEFAULT 'none',
    recurrence_interval INTEGER,
    parent_id          INTEGER,
    CONSTRAINT fk_tasks_owner
        FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_tasks_project
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL,
    CONSTRAINT fk_tasks_parent
        FOREIGN KEY(parent_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- association tables: many-to-many between tasks/users and projects/users ----

CREATE TABLE task_collaborators (
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (task_id, user_id),
    CONSTRAINT fk_tc_task FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_tc_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE project_collaborators (
    project_id INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    PRIMARY KEY (project_id, user_id),
    CONSTRAINT fk_pc_project FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_pc_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ATTACHMENTS ---------------------------------------------------------------

CREATE TABLE attachments (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filename   VARCHAR(255) NOT NULL,
    content    BYTEA NOT NULL,
    task_id    INTEGER,
    project_id INTEGER,
    CONSTRAINT fk_attachments_task
        FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT fk_attachments_project
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
);

-- COMMENTS -----------------------------------------------------------------

CREATE TABLE comments (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id    INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    content    TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT fk_comments_task FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_comments_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- NOTIFICATIONS ------------------------------------------------------------

CREATE TABLE notifications (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    task_id             INTEGER,
    project_id          INTEGER,
    type                notificationtype_enum NOT NULL DEFAULT 'due_date_reminder',
    payload             JSONB NOT NULL DEFAULT '{}'::jsonb,
    trigger_days_before INTEGER,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    comment_id          INTEGER,
    CONSTRAINT fk_notifications_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_task FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_project FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_comment FOREIGN KEY(comment_id) REFERENCES comments(id) ON DELETE CASCADE,
    CONSTRAINT uq_notification_unique_trigger UNIQUE (user_id, task_id, trigger_days_before, type)
);

-- Indexes ------------------------------------------------------------------

CREATE INDEX ix_notification_user_isread_created ON notifications (user_id, is_read, created_at);
CREATE INDEX idx_tasks_duedate ON tasks (duedate);
CREATE INDEX idx_projects_deadline ON projects (deadline);
-- End of script ------------------------------------------------------------
