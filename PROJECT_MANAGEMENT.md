# Project Management

This document describes the GitHub project management setup for the Scheduler Export project.

## Quick Links

- **Repository**: https://github.com/scttfrdmn/scheduler-job-export
- **Issues**: https://github.com/scttfrdmn/scheduler-job-export/issues
- **Project Board**: https://github.com/users/scttfrdmn/projects/24
- **Milestones**: https://github.com/scttfrdmn/scheduler-job-export/milestones
- **Actions**: https://github.com/scttfrdmn/scheduler-job-export/actions

## Labels

### Type Labels
- `type: bug` - Something isn't working
- `type: enhancement` - New feature or request
- `type: documentation` - Improvements or additions to documentation
- `type: security` - Security-related issue or improvement
- `type: testing` - Testing improvements or additions
- `type: refactor` - Code refactoring or cleanup

### Priority Labels
- `priority: critical` - Must be fixed immediately
- `priority: high` - High priority
- `priority: medium` - Medium priority
- `priority: low` - Low priority

### Status Labels
- `status: in progress` - Work is currently in progress
- `status: blocked` - Blocked by another issue or dependency
- `status: ready` - Ready to be worked on
- `status: needs review` - Needs code review or feedback

### Scheduler Labels
- `scheduler: slurm` - SLURM-specific
- `scheduler: pbs` - PBS/Torque-specific
- `scheduler: lsf` - LSF-specific
- `scheduler: uge` - UGE/SGE-specific
- `scheduler: htcondor` - HTCondor-specific

### Component Labels
- `component: export` - Data export scripts
- `component: anonymization` - Data anonymization
- `component: validation` - Input validation and security
- `component: ci/cd` - CI/CD and automation
- `component: testing` - Test infrastructure

### Special Labels
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention is needed
- `question` - Further information is requested

## Milestones

### v1.0 - Production Ready (Due: 2026-06-30)
Production-ready release with all core features stable.

**Issues:**
- #7 Address ShellCheck style recommendations
- #8 Refactor export scripts to reduce code duplication

### v1.1 - Enhanced Testing (Due: 2026-09-30)
Enhanced testing infrastructure and coverage.

**Issues:**
- #1 Add unit tests for Python functions
- #2 Add integration tests with mock scheduler data
- #4 Add code coverage reporting
- #5 Create Docker-based testing environment

### v1.2 - Performance & Scale (Due: 2026-12-31)
Performance improvements and large-scale testing.

**Issues:**
- #3 Add performance benchmarks and profiling

### Future Enhancements
Ideas for future consideration.

**Issues:**
- #6 Add multi-scheduler CI testing matrix
- #9 Add configurable output formats (CSV, JSON, Parquet)
- #10 Support incremental exports with state tracking

## Current Issues

### High Priority
- **#2** Add integration tests with mock scheduler data
- **#10** Support incremental exports with state tracking

### Medium Priority
- **#1** Add unit tests for Python functions
- **#3** Add performance benchmarks and profiling
- **#4** Add code coverage reporting
- **#5** Create Docker-based testing environment
- **#8** Refactor export scripts to reduce code duplication
- **#9** Add configurable output formats (CSV, JSON, Parquet)

### Low Priority
- **#6** Add multi-scheduler CI testing matrix
- **#7** Address ShellCheck style recommendations

### Good First Issues
- **#5** Create Docker-based testing environment
- **#7** Address ShellCheck style recommendations

## Workflow

### Creating Issues

```bash
# Create a new issue
gh issue create --title "Issue title" \
  --body "Issue description" \
  --label "type: bug" \
  --label "priority: high" \
  --milestone "v1.0 - Production Ready"
```

### Working on Issues

1. **Assign yourself**: `gh issue edit <number> --add-assignee @me`
2. **Add status label**: Add `status: in progress`
3. **Create branch**: `git checkout -b issue-<number>-short-description`
4. **Work on the issue**: Make your changes
5. **Reference issue in commits**: `git commit -m "Fix #<number>: description"`
6. **Create PR**: `gh pr create --title "..." --body "Closes #<number>"`
7. **Mark needs review**: Add `status: needs review` label

### Code Review

1. Review changes
2. Request changes if needed
3. Approve and merge when ready
4. Issue closes automatically via "Closes #<number>" in PR

### Closing Issues

Issues close automatically when:
- PR with "Closes #<number>" or "Fixes #<number>" is merged
- Manual close: `gh issue close <number>`

## Project Board

The project board provides a visual overview of work in progress:
https://github.com/users/scttfrdmn/projects/24

### Typical Board Views
- **Status**: Todo, In Progress, Done
- **Priority**: Critical, High, Medium, Low
- **Milestone**: v1.0, v1.1, v1.2, Future

## GitHub CLI Commands

### Issues
```bash
# List issues
gh issue list

# List issues by label
gh issue list --label "type: bug"

# List issues by milestone
gh issue list --milestone "v1.0 - Production Ready"

# View issue
gh issue view 1

# Create issue
gh issue create

# Edit issue
gh issue edit 1 --add-label "priority: high"

# Close issue
gh issue close 1
```

### Milestones
```bash
# List milestones
gh milestone list

# Create milestone
gh milestone create --title "v2.0" --due-date "2027-06-30"
```

### Labels
```bash
# List labels
gh label list

# Create label
gh label create "new-label" --description "Description" --color "ff0000"
```

### Projects
```bash
# List projects
gh project list --owner scttfrdmn

# View project
gh project view 24
```

## Best Practices

### Issue Creation
1. **Clear title**: Use descriptive titles that summarize the issue
2. **Detailed description**: Include context, steps to reproduce, expected behavior
3. **Proper labels**: Add appropriate type, priority, and component labels
4. **Assign milestone**: Link to relevant milestone if applicable
5. **Link related issues**: Use "Relates to #<number>" to link related issues

### Branch Naming
- Feature: `feature/<issue-number>-short-description`
- Bug fix: `fix/<issue-number>-short-description`
- Refactor: `refactor/<issue-number>-short-description`
- Documentation: `docs/<issue-number>-short-description`

### Commit Messages
- Reference issues: `Fix #123: Description` or `Closes #123: Description`
- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- Be descriptive: Explain what and why, not just how

### Pull Requests
- Link to issue: "Closes #<number>" in description
- Describe changes clearly
- Include test results
- Update documentation if needed
- Request review from maintainers

## Security

Security issues should be handled carefully:

1. **Don't create public issues** for security vulnerabilities
2. **Use GitHub Security Advisories** or email maintainers directly
3. **Add `type: security` label** only after issue is resolved
4. **Document fixes** in SECURITY.md

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

For questions about project management:
- Check existing issues first
- Use `question` label for clarifications
- Tag maintainers if urgent

---

**Last updated:** 2026-02-12
