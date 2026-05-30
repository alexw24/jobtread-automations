const FILE_ID = "";        // paste file ID here
const OLD_TAG_ID = "22PUwpZ5rKjf";     // tag ID to remove
const NEW_TAG_ID = "22PUwpbaY9et";     // tag ID to add
const GRANT_KEY = "22TJC5HGU5NYLJNsG42PzsxeNAn8ptsMLV";

const API_URL = "https://api.jobtread.com/pave";

async function paveQuery(queryBody) {
  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: { $: { grantKey: GRANT_KEY }, ...queryBody },
    }),
  });
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return { _raw: text, _status: res.status };
  }
}

async function swapTag() {
  // Step 1: Get the file's current tags by querying through the org's files
  const queryData = await paveQuery({
    currentGrant: {
      organization: {
        files: {
          $: {
            where: { "=": [{ field: "id" }, FILE_ID] },
            size: 1,
          },
          nodes: {
            id: {},
            fileTags: {
              nodes: {
                id: {},
              },
            },
          },
        },
      },
    },
  });

  const file = queryData?.currentGrant?.organization?.files?.nodes?.[0];
  if (!file) {
    return { error: "File not found", debug: queryData };
  }

  const currentTagIds = file.fileTags.nodes.map((t) => t.id);

  // Step 2: Remove old tag, add new tag
  const newTagIds = currentTagIds.filter((id) => id !== OLD_TAG_ID);
  if (!newTagIds.includes(NEW_TAG_ID)) {
    newTagIds.push(NEW_TAG_ID);
  }

  // Step 3: Update the file
  const updateData = await paveQuery({
    updateFile: {
      $: {
        id: FILE_ID,
        fileTagIds: newTagIds,
      },
    },
  });

  return updateData;
}

const result = await swapTag();
output = result;
