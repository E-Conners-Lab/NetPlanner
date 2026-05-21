import { useState } from 'react';
import Input from '../ui/Input.jsx';
import Button from '../ui/Button.jsx';

const DEVICE_CATEGORIES = [
  { value: 'access_point', label: 'Access Point' },
  { value: 'switch', label: 'Switch' },
  { value: 'router', label: 'Router' },
  { value: 'firewall', label: 'Firewall' },
  { value: 'server', label: 'Server' },
  { value: 'other', label: 'Other' },
];

const EMPTY_VALUES = {
  scenario_name: '',
  device_count: '',
  hardware_cost_per_unit: '',
  licensing_cost_per_unit_year: '',
  support_cost_year_one: '',
  lifecycle_years: '5',
  device_category: 'access_point',
  // PID amendment 1.3 — additional cost categories (all optional, default 0).
  installation_cost: '',
  accessories_cost_per_unit: '',
  spares_percent: '',
  training_cost: '',
  support_cost_recurring_per_year: '',
  adjacent_recurring_cost_per_year: '',
};

/** Fields that are non-negative-number-or-blank (blank → 0). */
const OPTIONAL_NONNEG_FIELDS = [
  'support_cost_year_one',
  'installation_cost',
  'accessories_cost_per_unit',
  'training_cost',
  'support_cost_recurring_per_year',
  'adjacent_recurring_cost_per_year',
];

/**
 * TcoInputForm — collects TCO inputs with inline client-side validation.
 *
 * @param {function} onCalculate  — called with { scenario_name, inputs } on valid submit
 * @param {boolean}  calculating  — disables the form while the preview request is in-flight
 */
export default function TcoInputForm({ onCalculate, calculating = false }) {
  const [values, setValues] = useState(EMPTY_VALUES);
  const [fieldErrors, setFieldErrors] = useState({});
  const [showAdvanced, setShowAdvanced] = useState(false);

  /* Immutable field update — clears the field error on change */
  const handleChange = (field) => (e) => {
    setValues((prev) => ({ ...prev, [field]: e.target.value }));
    if (fieldErrors[field]) {
      setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const validate = () => {
    const errors = {};

    if (!values.scenario_name.trim()) {
      errors.scenario_name = 'Scenario name is required.';
    }

    const deviceCount = Number(values.device_count);
    if (!values.device_count.trim()) {
      errors.device_count = 'Device count is required.';
    } else if (
      !Number.isInteger(deviceCount) ||
      deviceCount <= 0 ||
      String(values.device_count).includes('.')
    ) {
      errors.device_count = 'Device count must be a positive whole number.';
    }

    const hwCost = Number(values.hardware_cost_per_unit);
    if (values.hardware_cost_per_unit.trim() === '') {
      errors.hardware_cost_per_unit = 'Hardware cost per unit is required.';
    } else if (Number.isNaN(hwCost) || hwCost < 0) {
      errors.hardware_cost_per_unit = 'Must be a number ≥ 0.';
    }

    const licCost = Number(values.licensing_cost_per_unit_year);
    if (values.licensing_cost_per_unit_year.trim() === '') {
      errors.licensing_cost_per_unit_year = 'Licensing cost is required.';
    } else if (Number.isNaN(licCost) || licCost < 0) {
      errors.licensing_cost_per_unit_year = 'Must be a number ≥ 0.';
    }

    // Generic ≥ 0 check for every optional money field.
    for (const field of OPTIONAL_NONNEG_FIELDS) {
      const raw = values[field];
      if (raw !== '' && raw.trim() !== '') {
        const n = Number(raw);
        if (Number.isNaN(n) || n < 0) {
          errors[field] = 'Must be a number ≥ 0.';
        }
      }
    }

    // Spares percent: 0–100 (matches Pydantic ge=0, le=100).
    if (values.spares_percent !== '' && values.spares_percent.trim() !== '') {
      const sp = Number(values.spares_percent);
      if (Number.isNaN(sp) || sp < 0 || sp > 100) {
        errors.spares_percent = 'Spares must be between 0 and 100 (%).';
      }
    }

    const years = Number(values.lifecycle_years);
    if (!Number.isInteger(years) || years < 1 || years > 5) {
      errors.lifecycle_years = 'Lifecycle must be between 1 and 5 years.';
    }

    return errors;
  };

  /** Convert a possibly-blank string field to a finite number, defaulting to 0. */
  const numOrZero = (raw) =>
    raw !== '' && raw.trim() !== '' ? parseFloat(raw) : 0;

  const handleSubmit = (e) => {
    e.preventDefault();

    const errors = validate();
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    const payload = {
      scenario_name: values.scenario_name.trim(),
      inputs: {
        device_count: parseInt(values.device_count, 10),
        hardware_cost_per_unit: parseFloat(values.hardware_cost_per_unit),
        licensing_cost_per_unit_year: parseFloat(values.licensing_cost_per_unit_year),
        support_cost_year_one: numOrZero(values.support_cost_year_one),
        lifecycle_years: parseInt(values.lifecycle_years, 10),
        device_category: values.device_category,
        // PID amendment 1.3 — additional cost categories.
        installation_cost: numOrZero(values.installation_cost),
        accessories_cost_per_unit: numOrZero(values.accessories_cost_per_unit),
        spares_percent: numOrZero(values.spares_percent),
        training_cost: numOrZero(values.training_cost),
        support_cost_recurring_per_year: numOrZero(values.support_cost_recurring_per_year),
        adjacent_recurring_cost_per_year: numOrZero(values.adjacent_recurring_cost_per_year),
      },
    };

    onCalculate(payload);
  };

  const selectBase = [
    'w-full rounded-md px-3 py-2 text-sm bg-bg text-text',
    'border border-[var(--border)] transition-colors duration-150',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
    'focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
    'disabled:opacity-40 disabled:cursor-not-allowed',
    'hover:border-textMuted/40',
  ].join(' ');

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <Input
        label="Scenario Name *"
        id="tco-scenario-name"
        placeholder="e.g. Campus Wi-Fi Refresh 2026"
        value={values.scenario_name}
        onChange={handleChange('scenario_name')}
        disabled={calculating}
        error={fieldErrors.scenario_name}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input
          label="Device Count *"
          id="tco-device-count"
          type="number"
          placeholder="e.g. 48"
          value={values.device_count}
          onChange={handleChange('device_count')}
          disabled={calculating}
          error={fieldErrors.device_count}
        />

        <div className="flex flex-col gap-1">
          <label htmlFor="tco-device-category" className="text-xs font-medium text-textMuted">
            Device Category
          </label>
          <select
            id="tco-device-category"
            value={values.device_category}
            onChange={handleChange('device_category')}
            disabled={calculating}
            className={selectBase}
          >
            {DEVICE_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input
          label="Hardware Cost / Unit (USD) *"
          id="tco-hardware-cost"
          type="number"
          placeholder="e.g. 1200"
          value={values.hardware_cost_per_unit}
          onChange={handleChange('hardware_cost_per_unit')}
          disabled={calculating}
          error={fieldErrors.hardware_cost_per_unit}
        />

        <Input
          label="Licensing Cost / Unit / Year (USD) *"
          id="tco-licensing-cost"
          type="number"
          placeholder="e.g. 180"
          value={values.licensing_cost_per_unit_year}
          onChange={handleChange('licensing_cost_per_unit_year')}
          disabled={calculating}
          error={fieldErrors.licensing_cost_per_unit_year}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input
          label="Support Cost — Year 1 (USD)"
          id="tco-support-cost"
          type="number"
          placeholder="e.g. 5000 (optional, defaults to 0)"
          value={values.support_cost_year_one}
          onChange={handleChange('support_cost_year_one')}
          disabled={calculating}
          error={fieldErrors.support_cost_year_one}
        />

        <div className="flex flex-col gap-1">
          <label htmlFor="tco-lifecycle" className="text-xs font-medium text-textMuted">
            Lifecycle Years (1–5)
          </label>
          <select
            id="tco-lifecycle"
            value={values.lifecycle_years}
            onChange={handleChange('lifecycle_years')}
            disabled={calculating}
            className={selectBase}
          >
            {[1, 2, 3, 4, 5].map((yr) => (
              <option key={yr} value={String(yr)}>
                {yr} {yr === 1 ? 'year' : 'years'}
              </option>
            ))}
          </select>
          {fieldErrors.lifecycle_years && (
            <p className="text-xs text-red-400">{fieldErrors.lifecycle_years}</p>
          )}
        </div>
      </div>

      {/* PID amendment 1.3 — additional cost categories, hidden by default. */}
      <div className="border-t border-[var(--border)]/60 pt-3">
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          className="flex items-center gap-1.5 text-xs font-medium text-textMuted hover:text-text transition-colors duration-150 focus:outline-none"
          aria-expanded={showAdvanced}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`transition-transform duration-150 ${showAdvanced ? 'rotate-90' : ''}`}
            aria-hidden="true"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          {showAdvanced ? 'Hide' : 'Show'} additional costs (installation, accessories, spares, …)
        </button>

        {showAdvanced && (
          <div className="mt-3 flex flex-col gap-4">
            <p className="text-xs text-textMuted/80">
              All fields below are optional. Leaving a field blank explicitly
              means $0 for that cost — no silent defaults.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Installation / Professional Services (USD, Y1)"
                id="tco-installation"
                type="number"
                placeholder="e.g. 25000 (one-time)"
                value={values.installation_cost}
                onChange={handleChange('installation_cost')}
                disabled={calculating}
                error={fieldErrors.installation_cost}
              />

              <Input
                label="Accessories / Unit (USD, Y1)"
                id="tco-accessories"
                type="number"
                placeholder="e.g. 40 (mounts, cables, optics, PoE)"
                value={values.accessories_cost_per_unit}
                onChange={handleChange('accessories_cost_per_unit')}
                disabled={calculating}
                error={fieldErrors.accessories_cost_per_unit}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Spares (% of device count, Y1)"
                id="tco-spares"
                type="number"
                placeholder="e.g. 10 = 10% extra units"
                value={values.spares_percent}
                onChange={handleChange('spares_percent')}
                disabled={calculating}
                error={fieldErrors.spares_percent}
              />

              <Input
                label="Migration / Training Labor (USD, Y1)"
                id="tco-training"
                type="number"
                placeholder="e.g. 4500 (one-time)"
                value={values.training_cost}
                onChange={handleChange('training_cost')}
                disabled={calculating}
                error={fieldErrors.training_cost}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Recurring Support / Year (USD, Y2+)"
                id="tco-support-recurring"
                type="number"
                placeholder="e.g. 6000 (annual after Y1)"
                value={values.support_cost_recurring_per_year}
                onChange={handleChange('support_cost_recurring_per_year')}
                disabled={calculating}
                error={fieldErrors.support_cost_recurring_per_year}
              />

              <Input
                label="Adjacent Recurring / Year (USD, Y1–Y5)"
                id="tco-adjacent-recurring"
                type="number"
                placeholder="e.g. NAC renewal at 8000/year"
                value={values.adjacent_recurring_cost_per_year}
                onChange={handleChange('adjacent_recurring_cost_per_year')}
                disabled={calculating}
                error={fieldErrors.adjacent_recurring_cost_per_year}
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-end pt-2">
        <Button variant="primary" type="submit" disabled={calculating}>
          {calculating ? 'Calculating…' : 'Calculate TCO'}
        </Button>
      </div>
    </form>
  );
}
