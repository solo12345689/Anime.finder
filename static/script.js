document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("search-form");
  const input = document.getElementById("query");
  const resultsDiv = document.getElementById("results");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return alert("Enter a search term!");

    resultsDiv.innerHTML = "<p>Searching...</p>";

    try {
      const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
      const data = await response.json();

      if (data.error) {
        resultsDiv.innerHTML = `<p>Error: ${data.error}</p>`;
        return;
      }

      if (!data.items || data.items.length === 0) {
        resultsDiv.innerHTML = "<p>No results found.</p>";
        return;
      }

      resultsDiv.innerHTML = data.items
        .map(
          (item) => `
        <div class="card">
          <img src="${item.cover}" alt="${item.title}">
          <h3>${item.title}</h3>
          <p>${item.genre || ""}</p>
          <button onclick="downloadVideo('${item.subjectId}')">⬇ Download</button>
        </div>
      `
        )
        .join("");
    } catch (err) {
      resultsDiv.innerHTML = `<p>Error: ${err.message}</p>`;
    }
  });
});

async function downloadVideo(id) {
  try {
    const res = await fetch(`/download/${id}`);
    const data = await res.json();
    alert(data.message || data.error);
  } catch (e) {
    alert("Download failed: " + e.message);
  }
}
