// Không export ./services ở đây: handlers và services cùng export các tên
// giống nhau (AcademyProgram, AcademyEnrollment, etc.), gây TypeScript
// ambiguous-export error. Handlers đã re-export các public type cần thiết;
// services là implementation detail nội bộ.
export * from "./handlers";
export * from "./models";
