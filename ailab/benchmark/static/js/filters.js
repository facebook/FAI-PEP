var string_operators = [
  'equal', 'not_equal', 'begins_with', 'not_begins_with',
  'contains', 'not_contains', 'ends_with', 'not_ends_with',
]

var integer_operators = [
  'equal', 'not_equal', 'less', 'less_or_equal',
  'greater', 'greater_or_equal', 'between',
]

var time_operators = integer_operators

var filters = [
  {
    id: 'control_commit',
    label: 'Control Commit',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'commit',
    label: 'Commit',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'framework',
    label: 'Framework',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'group',
    label: 'Group',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'identifier',
    label: 'Identifier',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'info_string',
    label: 'Info String',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'metric',
    label: 'Metric',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'model',
    label: 'Model',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'platform',
    label: 'Platform',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'platform_hash',
    label: 'Platform Hash',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'type',
    label: 'Type',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'unit',
    label: 'Unit',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'user',
    label: 'User',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'user_identifier',
    label: 'User Identifier',
    type: 'string',
    operators: string_operators,
  },
  {
    id: 'num_runs',
    label: 'Num of Runs',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'time',
    label: 'Time',
    type: 'time',
    operators: time_operators,
  },
  {
    id: 'control_commit_time',
    label: 'Control Commit Time',
    type: 'time',
    operators: time_operators,
  },
  {
    id: 'commit_time',
    label: 'Commit Time',
    type: 'time',
    operators: time_operators,
  },
  {
    id: 'control_stdev',
    label: 'Control Stdev',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'stdev',
    label: 'Stdev',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'control_mean',
    label: 'Control Mean',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'mean',
    label: 'Mean',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'diff_mean',
    label: 'Diff Mean',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'control_p0',
    label: 'Control P0',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'p0',
    label: 'P0',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'diff_p0',
    label: 'Diff P0',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'control_p10',
    label: 'Control P10',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'p10',
    label: 'P10',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'diff_p10',
    label: 'Diff P10',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'control_p50',
    label: 'Control P50',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'p50',
    label: 'P50',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'diff_p50',
    label: 'Diff P50',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'control_p90',
    label: 'Control P90',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'p90',
    label: 'P90',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'diff_p90',
    label: 'Diff P90',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'control_p100',
    label: 'Control P100',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'p100',
    label: 'P100',
    type: 'integer',
    operators: integer_operators,
  },
  {
    id: 'diff_p100',
    label: 'Diff P100',
    type: 'integer',
    operators: integer_operators,
  },
]
