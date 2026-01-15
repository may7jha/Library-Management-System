# app.py
import streamlit as st
import json
import random
import string
from pathlib import Path
from datetime import datetime

# ---------- Config ----------
DATABASE = Path("library.json")

# ---------- Helpers ----------
def gen_id(prefix="B"):
    rand = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
    return f"{prefix}-{rand}"

def load_data():
    # initialize default structure
    default = {"books": [], "members": []}
    if DATABASE.exists():
        raw = DATABASE.read_text().strip()
        if raw:
            try:
                data = json.loads(raw)
            except Exception:
                data = default
        else:
            data = default
    else:
        data = default
        save_data(data)
    # Normalize/migrate older typos: 'borowed' -> 'borrowed'
    for m in data.get("members", []):
        if "borowed" in m and "borrowed" not in m:
            m["borrowed"] = m.pop("borowed")
        # ensure borrowed exists
        if "borrowed" not in m:
            m["borrowed"] = []
    return data

def save_data(data):
    DATABASE.write_text(json.dumps(data, indent=4, default=str))

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------- Load data ----------
data = load_data()

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Library Management", layout="wide")
st.title("📚 Library Management (Streamlit)")

menu = st.sidebar.selectbox("Choose action", [
    "Dashboard",
    "Add Book",
    "List Books",
    "Add Member",
    "List Members",
    "Borrow Book",
    "Return Book",
])

# ---------- Dashboard ----------
if menu == "Dashboard":
    st.subheader("Library overview")
    total_books = sum(b.get("total_copies", 0) for b in data["books"])
    available_books = sum(b.get("available_copies", 0) for b in data["books"])
    total_members = len(data["members"])
    st.metric("Total book copies", total_books)
    st.metric("Available copies", available_books)
    st.metric("Total members", total_members)

    st.markdown("### Recent Books")
    recent = sorted(data["books"], key=lambda x: x.get("added_on",""), reverse=True)[:10]
    if recent:
        st.table([{
            "id": b["id"],
            "title": b["title"],
            "author": b["author"],
            "available/total": f"{b.get('available_copies',0)}/{b.get('total_copies',0)}",
            "added_on": b.get("added_on","")
        } for b in recent])
    else:
        st.write("No books yet.")

# ---------- Add Book ----------
elif menu == "Add Book":
    st.subheader("Add a new book")
    with st.form("add_book"):
        title = st.text_input("Title")
        author = st.text_input("Author")
        copies = st.number_input("Number of copies", min_value=1, step=1, value=1)
        submitted = st.form_submit_button("Add book")
        if submitted:
            book = {
                "id": gen_id("B"),
                "title": title.strip(),
                "author": author.strip(),
                "total_copies": int(copies),
                "available_copies": int(copies),
                "added_on": now_str()
            }
            data["books"].append(book)
            save_data(data)
            st.success(f"Book added: {book['id']} — {book['title']}")
            st.experimental_rerun()

# ---------- List Books ----------
elif menu == "List Books":
    st.subheader("All books")
    if not data["books"]:
        st.info("No books available.")
    else:
        # Show a nice table
        books_table = [{
            "ID": b["id"],
            "Title": b["title"],
            "Author": b["author"],
            "Available": b.get("available_copies", 0),
            "Total": b.get("total_copies", 0),
            "Added on": b.get("added_on","")
        } for b in data["books"]]
        st.dataframe(books_table, use_container_width=True)

        # Optional: edit copies (small inline controls)
        st.markdown("---")
        st.write("Adjust copies for a book")
        book_ids = [f"{b['id']} — {b['title']}" for b in data["books"]]
        choice = st.selectbox("Select book to edit", [""] + book_ids)
        if choice:
            bid = choice.split(" — ")[0]
            book = next(b for b in data["books"] if b["id"] == bid)
            col1, col2, col3 = st.columns(3)
            with col1:
                new_total = st.number_input("Total copies", min_value=0, value=book.get("total_copies",0), key="total_"+bid)
            with col2:
                new_available = st.number_input("Available copies", min_value=0, value=book.get("available_copies",0), key="avail_"+bid)
            with col3:
                if st.button("Save changes", key="save_"+bid):
                    book["total_copies"] = int(new_total)
                    book["available_copies"] = int(new_available)
                    save_data(data)
                    st.success("Book updated")
                    st.experimental_rerun()

# ---------- Add Member ----------
elif menu == "Add Member":
    st.subheader("Add a new member")
    with st.form("add_member"):
        name = st.text_input("Member name")
        email = st.text_input("Email")
        submitted = st.form_submit_button("Add member")
        if submitted:
            member = {
                "id": gen_id("M"),
                "name": name.strip(),
                "email": email.strip(),
                "borrowed": []
            }
            data["members"].append(member)
            save_data(data)
            st.success(f"Member added: {member['id']} — {member['name']}")
            st.experimental_rerun()

# ---------- List Members ----------
elif menu == "List Members":
    st.subheader("All members")
    if not data["members"]:
        st.info("No members yet.")
    else:
        members_table = [{
            "ID": m["id"],
            "Name": m["name"],
            "Email": m.get("email",""),
            "Borrowed count": len(m.get("borrowed", []))
        } for m in data["members"]]
        st.dataframe(members_table, use_container_width=True)

        st.markdown("---")
        st.write("View a member's borrowed books")
        member_choice = st.selectbox("Select member", [""] + [f"{m['id']} — {m['name']}" for m in data["members"]])
        if member_choice:
            mid = member_choice.split(" — ")[0]
            member = next(m for m in data["members"] if m["id"] == mid)
            borrowed = member.get("borrowed", [])
            if not borrowed:
                st.write("No borrowed books")
            else:
                st.table([{
                    "book_id": b["book_id"],
                    "title": b["title"],
                    "borrow_on": b.get("borrow_on","")
                } for b in borrowed])

# ---------- Borrow Book ----------
elif menu == "Borrow Book":
    st.subheader("Borrow a book")
    if not data["members"]:
        st.warning("Add members first.")
    elif not data["books"]:
        st.warning("Add books first.")
    else:
        member_option = st.selectbox("Select member", [f"{m['id']} — {m['name']}" for m in data["members"]])
        # Only books with available copies > 0
        available_books = [b for b in data["books"] if b.get("available_copies", 0) > 0]
        if not available_books:
            st.info("No available copies to borrow.")
        else:
            book_option = st.selectbox("Select book", [f"{b['id']} — {b['title']} ({b.get('available_copies',0)} avail)" for b in available_books])
            if st.button("Borrow"):
                mid = member_option.split(" — ")[0]
                bid = book_option.split(" — ")[0]
                member = next(m for m in data["members"] if m["id"] == mid)
                book = next(b for b in data["books"] if b["id"] == bid)
                # Create borrow entry
                borrow_entry = {
                    "book_id": book["id"],
                    "title": book["title"],
                    "borrow_on": now_str()
                }
                member.setdefault("borrowed", []).append(borrow_entry)
                book["available_copies"] = max(0, book.get("available_copies", 0) - 1)
                save_data(data)
                st.success(f"{member['name']} borrowed {book['title']}")
                st.experimental_rerun()

# ---------- Return Book ----------
elif menu == "Return Book":
    st.subheader("Return a borrowed book")
    if not data["members"]:
        st.info("No members")
    else:
        member_option = st.selectbox("Select member", [""] + [f"{m['id']} — {m['name']}" for m in data["members"]])
        if member_option:
            mid = member_option.split(" — ")[0]
            member = next(m for m in data["members"] if m["id"] == mid)
            borrowed = member.get("borrowed", [])
            if not borrowed:
                st.write("This member has no borrowed books.")
            else:
                choice = st.selectbox("Select borrowed book to return", [f"{i+1}. {b['title']} ({b['book_id']}) — {b.get('borrow_on','')}" for i,b in enumerate(borrowed)])
                if st.button("Return"):
                    idx = int(choice.split(".")[0]) - 1
                    if 0 <= idx < len(borrowed):
                        selected = member["borrowed"].pop(idx)
                        # find book and increase available
                        book_list = [bk for bk in data["books"] if bk["id"] == selected["book_id"]]
                        if book_list:
                            book_list[0]["available_copies"] = book_list[0].get("available_copies", 0) + 1
                        save_data(data)
                        st.success(f"Returned: {selected['title']}")
                        st.experimental_rerun()
                    else:
                        st.error("Invalid selection")

# End of file
