import { useState } from 'react';
import Input from '../ui/Input.jsx';
import Button from '../ui/Button.jsx';

const EMPTY_VALUES = {
  name: '',
  company: '',
  description: '',
  existing_infra: '',
  budget_ceiling: '',
};

/**
 * ProjectForm — create and edit form for a project.
 *
 * @param {object}   [initialValues] — prefill for edit mode
 * @param {function} onSubmit        — called with validated form data object
 * @param {function} onCancel        — called when user cancels
 * @param {boolean}  [submitting]    — disables form during async submit
 */
export default function ProjectForm({
  initialValues,
  onSubmit,
  onCancel,
  submitting = false,
}) {
  const initial = {
    ...EMPTY_VALUES,
    ...initialValues,
    /* budget_ceiling: store as string for the input, convert on submit */
    budget_ceiling:
      initialValues?.budget_ceiling != null
        ? String(initialValues.budget_ceiling)
        : '',
  };

  const [values, setValues] = useState(initial);
  const [fieldErrors, setFieldErrors] = useState({});

  /* Immutable field update helper */
  const handleChange = (field) => (e) => {
    setValues((prev) => ({ ...prev, [field]: e.target.value }));
    /* Clear the field error on change */
    if (fieldErrors[field]) {
      setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  /* Client-side validation */
  const validate = () => {
    const errors = {};

    if (!values.name.trim()) {
      errors.name = 'Project name is required.';
    }

    if (values.budget_ceiling !== '') {
      const num = Number(values.budget_ceiling);
      if (Number.isNaN(num)) {
        errors.budget_ceiling = 'Budget must be a number.';
      } else if (num < 0) {
        errors.budget_ceiling = 'Budget must be 0 or greater.';
      }
    }

    return errors;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const errors = validate();
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    /* Build the payload — only include budget if provided */
    const payload = {
      name: values.name.trim(),
      company: values.company.trim(),
      description: values.description.trim(),
      existing_infra: values.existing_infra.trim(),
      budget_ceiling:
        values.budget_ceiling !== '' ? Number(values.budget_ceiling) : null,
    };

    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <Input
        label="Project Name *"
        id="project-name"
        placeholder="e.g. Campus LAN Refresh"
        value={values.name}
        onChange={handleChange('name')}
        disabled={submitting}
        error={fieldErrors.name}
      />

      <Input
        label="Company"
        id="project-company"
        placeholder="e.g. Acme Corp"
        value={values.company}
        onChange={handleChange('company')}
        disabled={submitting}
        error={fieldErrors.company}
      />

      <div className="flex flex-col gap-1">
        <label htmlFor="project-description" className="text-xs font-medium text-textMuted">
          Description
        </label>
        <textarea
          id="project-description"
          rows={3}
          placeholder="Brief summary of the project goals…"
          value={values.description}
          onChange={handleChange('description')}
          disabled={submitting}
          className={[
            'w-full rounded-md px-3 py-2 text-sm bg-bg text-text resize-y',
            'border transition-colors duration-150',
            'placeholder:text-textMuted/50',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            'border-[var(--border)] hover:border-textMuted/40',
          ].join(' ')}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="project-existing-infra" className="text-xs font-medium text-textMuted">
          Existing Infrastructure
        </label>
        <textarea
          id="project-existing-infra"
          rows={3}
          placeholder="Describe the current network environment…"
          value={values.existing_infra}
          onChange={handleChange('existing_infra')}
          disabled={submitting}
          className={[
            'w-full rounded-md px-3 py-2 text-sm bg-bg text-text resize-y',
            'border transition-colors duration-150',
            'placeholder:text-textMuted/50',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            'border-[var(--border)] hover:border-textMuted/40',
          ].join(' ')}
        />
      </div>

      <Input
        label="Budget Ceiling (USD)"
        id="project-budget"
        type="number"
        placeholder="e.g. 250000"
        value={values.budget_ceiling}
        onChange={handleChange('budget_ceiling')}
        disabled={submitting}
        error={fieldErrors.budget_ceiling}
      />

      <div className="flex items-center justify-end gap-3 pt-2">
        <Button variant="secondary" type="button" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button variant="primary" type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : (initialValues ? 'Save Changes' : 'Create Project')}
        </Button>
      </div>
    </form>
  );
}
