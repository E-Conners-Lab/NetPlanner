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
};

/**
 * TcoInputForm — collects TCO inputs with inline client-side validation.
 *
 * @param {function} onCalculate  — called with { scenario_name, inputs } on valid submit
 * @param {boolean}  calculating  — disables the form while the preview request is in-flight
 */
export default function TcoInputForm({ onCalculate, calculating = false }) {
  const [values, setValues] = useState(EMPTY_VALUES);
  const [fieldErrors, setFieldErrors] = useState({});

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

    if (values.support_cost_year_one.trim() !== '') {
      const supCost = Number(values.support_cost_year_one);
      if (Number.isNaN(supCost) || supCost < 0) {
        errors.support_cost_year_one = 'Must be a number ≥ 0.';
      }
    }

    const years = Number(values.lifecycle_years);
    if (!Number.isInteger(years) || years < 1 || years > 5) {
      errors.lifecycle_years = 'Lifecycle must be between 1 and 5 years.';
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

    const payload = {
      scenario_name: values.scenario_name.trim(),
      inputs: {
        device_count: parseInt(values.device_count, 10),
        hardware_cost_per_unit: parseFloat(values.hardware_cost_per_unit),
        licensing_cost_per_unit_year: parseFloat(values.licensing_cost_per_unit_year),
        support_cost_year_one:
          values.support_cost_year_one.trim() !== ''
            ? parseFloat(values.support_cost_year_one)
            : 0,
        lifecycle_years: parseInt(values.lifecycle_years, 10),
        device_category: values.device_category,
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

      <div className="flex items-center justify-end pt-2">
        <Button variant="primary" type="submit" disabled={calculating}>
          {calculating ? 'Calculating…' : 'Calculate TCO'}
        </Button>
      </div>
    </form>
  );
}
